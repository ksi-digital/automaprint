"""
Cloudflare Tunnel management for AutomaPrint
Auto-downloads cloudflared and manages tunnel lifecycle
"""

import os
import sys
import re
import platform
import subprocess
import threading
import urllib.request

from . import config as cfg

CLOUDFLARED_FILENAME = "cloudflared.exe"


def get_cloudflared_url():
    """Get the correct cloudflared download URL based on system architecture"""
    arch = platform.machine().lower()

    # Check for 64-bit
    if arch in ('amd64', 'x86_64', 'x64'):
        return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    # Check for 32-bit
    elif arch in ('i386', 'i686', 'x86'):
        return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-386.exe"
    # Check for ARM64
    elif arch in ('arm64', 'aarch64'):
        return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-arm64.exe"
    else:
        # Default to 64-bit, most common
        return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"


def get_cloudflared_path():
    """Get path to cloudflared executable"""
    # Check in app data directory
    data_dir = cfg.get_data_dir()
    exe_path = os.path.join(data_dir, CLOUDFLARED_FILENAME)

    if os.path.exists(exe_path):
        return exe_path

    # Check in assets folder (development)
    if hasattr(sys, '_MEIPASS'):
        bundled = os.path.join(sys._MEIPASS, CLOUDFLARED_FILENAME)
        if os.path.exists(bundled):
            return bundled
    else:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assets_path = os.path.join(script_dir, 'assets', CLOUDFLARED_FILENAME)
        if os.path.exists(assets_path):
            return assets_path

    return None


def download_cloudflared(log_callback=None, force_update=False):
    """Download cloudflared executable

    Args:
        log_callback: Optional logging callback function
        force_update: If True, re-download even if already exists
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    data_dir = cfg.get_data_dir()
    exe_path = os.path.join(data_dir, CLOUDFLARED_FILENAME)

    if os.path.exists(exe_path) and not force_update:
        log("[OK] cloudflared already downloaded")
        return exe_path

    if force_update and os.path.exists(exe_path):
        log("[UPDATE] Updating cloudflared...")
        try:
            os.unlink(exe_path)
        except Exception as e:
            log(f"[ERROR] Could not remove old version: {e}")
            return None

    url = get_cloudflared_url()
    arch = platform.machine()
    log(f"[DOWNLOAD] Downloading cloudflared for {arch}...")

    try:
        # Download with progress
        def report_progress(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, block_num * block_size * 100 // total_size)
                if block_num % 50 == 0:  # Log every 50 blocks
                    log(f"[DOWNLOAD] {percent}%")

        urllib.request.urlretrieve(url, exe_path, report_progress)

        log(f"[OK] cloudflared {'updated' if force_update else 'downloaded'}")
        return exe_path

    except Exception as e:
        log(f"[ERROR] Failed to download cloudflared: {e}")
        return None


class TunnelManager:
    """Manages Cloudflare tunnel lifecycle"""

    def __init__(self, log_callback=None):
        self.process = None
        self.tunnel_url = None
        self.running = False
        self.log_callback = log_callback
        self._output_thread = None

    def log(self, msg):
        print(msg)
        if self.log_callback:
            self.log_callback(msg)

    def start(self, local_port):
        """Start tunnel to local port"""
        if self.running:
            self.log("[WARN] Tunnel already running")
            return False

        # Get or download cloudflared
        cloudflared = get_cloudflared_path()
        if not cloudflared:
            self.log("[TUNNEL] Downloading cloudflared...")
            cloudflared = download_cloudflared(self.log_callback)
            if not cloudflared:
                return False

        self.log(f"[TUNNEL] Starting tunnel to localhost:{local_port}...")

        try:
            # Start cloudflared quick tunnel
            cmd = [
                cloudflared,
                'tunnel',
                '--url', f'http://localhost:{local_port}'
            ]

            # Start process with pipe for output
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            self.running = True

            # Start thread to capture output and find URL
            self._output_thread = threading.Thread(target=self._capture_output, daemon=True)
            self._output_thread.start()

            return True

        except Exception as e:
            self.log(f"[ERROR] Failed to start tunnel: {e}")
            return False

    def _capture_output(self):
        """Capture tunnel output and extract URL"""
        url_pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com')

        try:
            for line in self.process.stdout:
                line = line.strip()
                if line:
                    # Look for tunnel URL
                    match = url_pattern.search(line)
                    if match and not self.tunnel_url:
                        self.tunnel_url = match.group(0)
                        self.log(f"[TUNNEL] URL: {self.tunnel_url}")

                    # Log other important messages
                    if 'error' in line.lower() or 'failed' in line.lower():
                        self.log(f"[TUNNEL] {line}")
        except:
            pass

        self.running = False
        self.tunnel_url = None

    def stop(self):
        """Stop the tunnel"""
        if self.process:
            self.log("[TUNNEL] Stopping tunnel...")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass

            self.process = None
            self.tunnel_url = None
            self.running = False
            self.log("[TUNNEL] Tunnel stopped")

    def get_url(self):
        """Get current tunnel URL"""
        return self.tunnel_url
