"""
SumatraPDF management for AutomaPrint
Auto-downloads SumatraPDF and manages executable
"""

import os
import sys
import platform
import zipfile
import urllib.request
import json

from . import config as cfg

SUMATRA_FILENAME = "SumatraPDF.exe"
# SumatraPDF releases: https://github.com/sumatrapdfreader/sumatrapdf/releases
# Fallback version if GitHub API fails
SUMATRA_FALLBACK_VERSION = "3.5.2"


def get_latest_version():
    """Fetch the latest SumatraPDF version from GitHub API"""
    try:
        api_url = "https://api.github.com/repos/sumatrapdfreader/sumatrapdf/releases/latest"
        with urllib.request.urlopen(api_url, timeout=5) as response:
            data = json.loads(response.read().decode())
            # GitHub tag format is usually just the version number (e.g., "3.5.2")
            tag_name = data.get('tag_name', '').lstrip('v')
            if tag_name:
                return tag_name
    except Exception as e:
        print(f"[WARN] Could not fetch latest SumatraPDF version: {e}")

    # Fall back to hardcoded version
    return SUMATRA_FALLBACK_VERSION


def get_sumatra_url(version=None):
    """Get the correct SumatraPDF download URL based on system architecture

    Args:
        version: Specific version to download, or None to fetch latest
    """
    if version is None:
        version = get_latest_version()

    arch = platform.machine().lower()

    # SumatraPDF provides 32-bit and 64-bit versions
    # 32-bit works on both, but 64-bit is faster on 64-bit systems
    if arch in ('amd64', 'x86_64', 'x64'):
        # 64-bit version
        return f"https://www.sumatrapdfreader.org/dl/rel/{version}/SumatraPDF-{version}-64.zip", version
    else:
        # 32-bit version (works on all Windows)
        return f"https://www.sumatrapdfreader.org/dl/rel/{version}/SumatraPDF-{version}.zip", version


def get_sumatra_path():
    """Get path to SumatraPDF executable"""
    # Check in app data directory first (downloaded location)
    data_dir = cfg.get_data_dir()
    exe_path = os.path.join(data_dir, SUMATRA_FILENAME)

    if os.path.exists(exe_path):
        return exe_path

    # Check in PyInstaller bundle (if bundled during build)
    if hasattr(sys, '_MEIPASS'):
        bundled = os.path.join(sys._MEIPASS, SUMATRA_FILENAME)
        if os.path.exists(bundled):
            return bundled

    # Check in assets folder (development - legacy)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_path = os.path.join(script_dir, 'assets', SUMATRA_FILENAME)
    if os.path.exists(assets_path):
        return assets_path

    # Also check for old versioned filename
    legacy_names = ['SumatraPDF-3.5.2-32.exe', 'SumatraPDF-3.5.2-64.exe']
    for legacy_name in legacy_names:
        legacy_path = os.path.join(data_dir, legacy_name)
        if os.path.exists(legacy_path):
            # Rename to standard name
            try:
                os.rename(legacy_path, exe_path)
                return exe_path
            except:
                return legacy_path

    return None


def download_sumatra(log_callback=None, force_update=False):
    """Download SumatraPDF executable

    Args:
        log_callback: Optional logging callback function
        force_update: If True, re-download even if already exists
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    data_dir = cfg.get_data_dir()
    exe_path = os.path.join(data_dir, SUMATRA_FILENAME)

    if os.path.exists(exe_path) and not force_update:
        log("[OK] SumatraPDF already downloaded")
        return exe_path

    if force_update and os.path.exists(exe_path):
        log("[UPDATE] Updating SumatraPDF...")
        try:
            os.unlink(exe_path)
        except Exception as e:
            log(f"[ERROR] Could not remove old version: {e}")
            return None

    # Get latest version and URL
    url, version = get_sumatra_url()
    arch = platform.machine()
    log(f"[DOWNLOAD] Downloading SumatraPDF {version} for {arch}...")

    try:
        # Download ZIP file
        zip_path = os.path.join(data_dir, "sumatra_temp.zip")

        def report_progress(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, block_num * block_size * 100 // total_size)
                if block_num % 50 == 0:  # Log every 50 blocks
                    log(f"[DOWNLOAD] {percent}%")

        urllib.request.urlretrieve(url, zip_path, report_progress)

        # Extract the EXE from ZIP
        log("[EXTRACT] Extracting SumatraPDF...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # SumatraPDF zip contains the exe directly
            for file_info in zip_ref.filelist:
                if file_info.filename.endswith('.exe'):
                    # Extract and rename to standard name
                    zip_ref.extract(file_info, data_dir)
                    extracted_path = os.path.join(data_dir, file_info.filename)

                    # Rename to standard name if needed
                    if extracted_path != exe_path:
                        os.rename(extracted_path, exe_path)
                    break

        # Cleanup ZIP file
        try:
            os.unlink(zip_path)
        except:
            pass

        log(f"[OK] SumatraPDF {version} {'updated' if force_update else 'downloaded'} and ready")
        return exe_path

    except Exception as e:
        log(f"[ERROR] Failed to download SumatraPDF: {e}")
        # Cleanup on failure
        try:
            if os.path.exists(zip_path):
                os.unlink(zip_path)
        except:
            pass
        return None


def get_sumatra_version():
    """Get the current/latest SumatraPDF version string"""
    return get_latest_version()
