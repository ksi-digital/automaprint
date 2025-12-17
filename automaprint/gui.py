"""
GUI Application for AutomaPrint
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog

from . import autostart
from . import test_client
from . import config as cfg
from . import sumatra
from . import tunnel
from .server import PrintServer
from .logging_setup import setup_logger, cleanup_old_logs

# Optional system tray support
try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


class AutomaPrintGUI:
    """Main GUI Application"""

    def __init__(self, root, auto_start_mode=False):
        self.root = root
        self.auto_start_mode = auto_start_mode
        self.root.title("AutomaPrint Server")
        self.root.geometry("1000x600")
        self.root.resizable(True, True)

        # Set window icon
        self._set_window_icon()

        # Initialize server
        self.server = PrintServer(log_callback=self.log_message)
        self.server_thread = None

        # Setup logging
        self.logger = setup_logger('gui')
        cleanup_old_logs()

        # GUI variables
        self.printer_var = tk.StringVar(value=self.server.config.get("printer_name", ""))
        self.port_var = tk.IntVar(value=self.server.config.get("port", 8080))
        self.test_url_var = tk.StringVar(value="http://localhost:8080")
        self.test_api_key_var = tk.StringVar(value="")

        # System tray
        self.tray_icon = None
        self.minimize_to_tray = self.server.config.get("minimize_to_tray", True)
        self.minimize_to_tray_var = tk.BooleanVar(value=self.minimize_to_tray)

        # Print settings variables
        self.scaling_var = tk.StringVar(value=self.server.config.get("print_scaling", "shrink"))
        self.color_var = tk.StringVar(value=self.server.config.get("print_color", "color"))
        self.duplex_var = tk.StringVar(value=self.server.config.get("print_duplex", "simplex"))

        # Tunnel settings
        self.use_tunnel_var = tk.BooleanVar(value=self.server.config.get("use_tunnel", False))
        self.tunnel_url = None

        # Create GUI
        self.create_widgets()
        self.update_status()

        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start status thread
        self.start_status_thread()

        # Setup tray
        if TRAY_AVAILABLE:
            self.setup_tray()

        # Check and download SumatraPDF at startup (after GUI is ready)
        self.root.after(100, self.check_sumatra_at_startup)

        # Auto-start handling
        if auto_start_mode:
            if TRAY_AVAILABLE:
                self.root.after(100, self.hide_window)
            self.root.after(2000, self.auto_start_server)
        elif self.server.config.get("printer_name"):
            self.log_message("Printer configured, auto-starting server...")
            self.root.after(1000, self.auto_start_server)

    def _set_window_icon(self):
        """Set the window icon"""
        try:
            # Check PyInstaller bundle first
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                # Development mode - check assets folder
                script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                icon_path = os.path.join(script_dir, 'assets', 'icon.ico')

            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not load icon: {e}")

    def check_sumatra_at_startup(self):
        """Check for SumatraPDF at startup and download if needed"""
        sumatra_path = sumatra.get_sumatra_path()

        if sumatra_path:
            self.log_message(f"[OK] SumatraPDF ready")
        else:
            self.log_message("[INFO] SumatraPDF not found, downloading...")
            # Download in a separate thread to avoid blocking UI
            def download_on_startup():
                result = sumatra.download_sumatra(log_callback=self.log_message)
                if result:
                    self.log_message(f"[OK] SumatraPDF ready")
                else:
                    self.log_message("[ERROR] Failed to download SumatraPDF")

            threading.Thread(target=download_on_startup, daemon=True).start()

    def create_widgets(self):
        """Create GUI widgets"""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Server tab
        server_frame = ttk.Frame(notebook)
        notebook.add(server_frame, text="Server")
        self.create_server_tab(server_frame)

        # Test tab
        test_frame = ttk.Frame(notebook)
        notebook.add(test_frame, text="Test Client")
        self.create_test_tab(test_frame)

        # Settings tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")
        self.create_settings_tab(settings_frame)

        # About tab
        about_frame = ttk.Frame(notebook)
        notebook.add(about_frame, text="About")
        self.create_about_tab(about_frame)

    def create_server_tab(self, parent):
        """Create server management tab"""
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        # Configuration
        config_frame = ttk.LabelFrame(top_frame, text="Configuration", padding="10")
        config_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ttk.Label(config_frame, text="Printer:").pack(anchor=tk.W)
        self.printer_combo = ttk.Combobox(config_frame, textvariable=self.printer_var, width=40)
        self.printer_combo['values'] = self.server.list_printers()
        self.printer_combo.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(config_frame, text="Port:").pack(anchor=tk.W)
        self.port_entry = ttk.Entry(config_frame, textvariable=self.port_var, width=10)
        self.port_entry.pack(anchor=tk.W, pady=(5, 10))

        self.save_config_btn = ttk.Button(config_frame, text="Save Configuration",
                   command=self.save_configuration)
        self.save_config_btn.pack(fill=tk.X)

        # Control
        control_frame = ttk.LabelFrame(top_frame, text="Server Control", padding="10")
        control_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))

        # Status with colored dot
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(pady=10)

        self.server_dot_label = tk.Label(status_frame, text="●", font=("Arial", 16), fg="red")
        self.server_dot_label.pack(side=tk.LEFT)

        self.server_status_label = ttk.Label(status_frame, text=" Server Stopped",
                                              font=("Arial", 12, "bold"))
        self.server_status_label.pack(side=tk.LEFT)

        # Server URL with copy button
        url_frame = ttk.Frame(control_frame)
        url_frame.pack(pady=5)

        self.server_info_label = ttk.Label(url_frame, text="", font=("Arial", 9))
        self.server_info_label.pack(side=tk.LEFT)

        self.copy_url_btn = ttk.Button(url_frame, text="📋", width=3,
                                        command=self.copy_server_url, state="disabled")
        self.copy_url_btn.pack(side=tk.LEFT, padx=(5, 0))

        # API Key display (only visible when tunnel active) - right below URL
        self.api_key_display_frame = ttk.Frame(control_frame)
        # Initially hidden, shown when tunnel URL is available

        api_key_row = ttk.Frame(self.api_key_display_frame)
        api_key_row.pack()

        self.api_key_var = tk.StringVar(value=self.server.config.get("api_key", ""))
        api_key_label = ttk.Label(api_key_row, textvariable=self.api_key_var,
                                  font=("Consolas", 8))
        api_key_label.pack(side=tk.LEFT)
        ttk.Button(api_key_row, text="📋", width=3,
                   command=self.copy_api_key).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(self.api_key_display_frame, text="Send as X-API-Key header",
                  font=("Arial", 7), foreground="gray").pack()

        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Server",
                                        command=self.start_server, width=15)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop Server",
                                       command=self.stop_server, width=15, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Remote Access Settings
        remote_frame = ttk.LabelFrame(parent, text="Remote Access", padding="10")
        remote_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        remote_row = ttk.Frame(remote_frame)
        remote_row.pack(fill=tk.X)

        self.tunnel_check = ttk.Checkbutton(
            remote_row,
            text="Enable Cloudflare Tunnel",
            variable=self.use_tunnel_var,
            command=self.on_tunnel_setting_changed
        )
        self.tunnel_check.pack(side=tk.LEFT)

        ttk.Button(remote_row, text="Regenerate API Key", width=18,
                   command=self.regenerate_api_key).pack(side=tk.RIGHT)

        # Log
        log_frame = ttk.LabelFrame(parent, text="Server Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_container, height=15, font=("Consolas", 9))
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_test_tab(self, parent):
        """Create test client tab"""
        config_frame = ttk.LabelFrame(parent, text="Test Configuration", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=10)

        config_grid = ttk.Frame(config_frame)
        config_grid.pack(fill=tk.X)

        ttk.Label(config_grid, text="Server URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_grid, textvariable=self.test_url_var, width=40).grid(
            row=0, column=1, sticky=tk.W, padx=(10, 20), pady=5)

        ttk.Button(config_grid, text="Test Connection", command=self.test_connection,
                   width=15).grid(row=0, column=2, padx=(10, 0), pady=5)

        ttk.Label(config_grid, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_grid, textvariable=self.test_api_key_var, width=40).grid(
            row=1, column=1, sticky=tk.W, padx=(10, 20), pady=5)

        ttk.Label(config_grid, text="Send as X-API-Key header (required for remote access)",
                  font=("Arial", 8), foreground="gray").grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # Test buttons
        test_frame = ttk.LabelFrame(parent, text="Test Actions", padding="10")
        test_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        button_frame = ttk.Frame(test_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Send Blank PDF",
                   command=self.send_blank_pdf).pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Select PDF File...",
                   command=self.send_selected_pdf).pack(side=tk.LEFT, padx=5)

        # Test log
        log_frame = ttk.LabelFrame(parent, text="Test Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.test_log_text = tk.Text(log_container, height=10, font=("Consolas", 9))
        test_scrollbar = ttk.Scrollbar(log_container, orient="vertical",
                                        command=self.test_log_text.yview)
        self.test_log_text.configure(yscrollcommand=test_scrollbar.set)

        self.test_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        test_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_settings_tab(self, parent):
        """Create settings tab"""
        # Print Settings
        print_frame = ttk.LabelFrame(parent, text="Print Settings", padding="10")
        print_frame.pack(fill=tk.X, padx=10, pady=10)

        # Create grid for dropdowns
        settings_grid = ttk.Frame(print_frame)
        settings_grid.pack(fill=tk.X)

        # Scaling
        ttk.Label(settings_grid, text="Page Scaling:").grid(row=0, column=0, sticky=tk.W, pady=5)
        scaling_values = list(cfg.SCALING_OPTIONS.values())
        self.scaling_combo = ttk.Combobox(settings_grid, textvariable=self.scaling_var,
                                          values=scaling_values, state="readonly", width=25)
        self.scaling_combo.set(cfg.SCALING_OPTIONS.get(self.scaling_var.get(), "Shrink Only"))
        self.scaling_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        self.scaling_combo.bind("<<ComboboxSelected>>", self.on_print_settings_changed)

        # Color
        ttk.Label(settings_grid, text="Color Mode:").grid(row=1, column=0, sticky=tk.W, pady=5)
        color_values = list(cfg.COLOR_OPTIONS.values())
        self.color_combo = ttk.Combobox(settings_grid, textvariable=self.color_var,
                                        values=color_values, state="readonly", width=25)
        self.color_combo.set(cfg.COLOR_OPTIONS.get(self.color_var.get(), "Color"))
        self.color_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        self.color_combo.bind("<<ComboboxSelected>>", self.on_print_settings_changed)

        # Duplex
        ttk.Label(settings_grid, text="Sides:").grid(row=2, column=0, sticky=tk.W, pady=5)
        duplex_values = list(cfg.DUPLEX_OPTIONS.values())
        self.duplex_combo = ttk.Combobox(settings_grid, textvariable=self.duplex_var,
                                         values=duplex_values, state="readonly", width=25)
        self.duplex_combo.set(cfg.DUPLEX_OPTIONS.get(self.duplex_var.get(), "Single-sided"))
        self.duplex_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        self.duplex_combo.bind("<<ComboboxSelected>>", self.on_print_settings_changed)

        # Application Settings
        app_frame = ttk.LabelFrame(parent, text="Application Settings", padding="10")
        app_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Auto-start checkbox
        is_autostart_enabled, _ = autostart.check_startup_status()
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled)
        autostart_check = ttk.Checkbutton(
            app_frame,
            text="Start automatically when Windows starts",
            variable=self.autostart_var,
            command=self.on_autostart_changed
        )
        autostart_check.pack(anchor=tk.W, pady=5)

        ttk.Label(app_frame, text="Note: Remote access tunnel URL changes on each restart",
                  font=("Arial", 8), foreground="gray").pack(anchor=tk.W, padx=(20, 0))

        minimize_check = ttk.Checkbutton(
            app_frame,
            text="Minimize to system tray when closing window",
            variable=self.minimize_to_tray_var,
            command=self.on_minimize_option_changed
        )
        minimize_check.pack(anchor=tk.W, pady=5)

        if not TRAY_AVAILABLE:
            minimize_check.config(state="disabled")
            ttk.Label(app_frame, text="(System tray not available)",
                      font=("Arial", 8), foreground="gray").pack(anchor=tk.W)

        # Software Updates
        updates_frame = ttk.LabelFrame(parent, text="Software Updates", padding="10")
        updates_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # SumatraPDF update
        sumatra_row = ttk.Frame(updates_frame)
        sumatra_row.pack(fill=tk.X, pady=5)

        sumatra_version = sumatra.get_sumatra_version()
        ttk.Label(sumatra_row, text=f"SumatraPDF (v{sumatra_version})",
                  font=("Arial", 10)).pack(side=tk.LEFT)

        ttk.Button(sumatra_row, text="Update SumatraPDF", width=20,
                   command=self.update_sumatra).pack(side=tk.RIGHT)

        # Cloudflared update
        cloudflared_row = ttk.Frame(updates_frame)
        cloudflared_row.pack(fill=tk.X, pady=5)

        ttk.Label(cloudflared_row, text="Cloudflare Tunnel (latest)",
                  font=("Arial", 10)).pack(side=tk.LEFT)

        ttk.Button(cloudflared_row, text="Update Cloudflare", width=20,
                   command=self.update_cloudflared).pack(side=tk.RIGHT)

        ttk.Label(updates_frame, text="Note: Updates download latest versions. Server must be stopped to apply.",
                  font=("Arial", 8), foreground="gray").pack(anchor=tk.W, pady=(10, 0))

    def create_about_tab(self, parent):
        """Create about tab with KSI Digital branding"""
        import webbrowser

        # Center container
        center_frame = ttk.Frame(parent)
        center_frame.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)

        # App name and version
        ttk.Label(center_frame, text="AutomaPrint", font=("Arial", 24, "bold")).pack(pady=(20, 5))
        ttk.Label(center_frame, text="Version 1.0", font=("Arial", 11), foreground="gray").pack()

        # Description
        desc_text = "A REST API server that receives PDF files over the network\nand prints them to a local printer."
        ttk.Label(center_frame, text=desc_text, font=("Arial", 10), justify=tk.CENTER).pack(pady=20)

        # API info
        api_frame = ttk.LabelFrame(center_frame, text="API Endpoints", padding="15")
        api_frame.pack(fill=tk.X, pady=10)

        api_text = """GET  /health  -  Health check (returns server status)
POST /print   -  Print a PDF file (send PDF as request body)

Headers:
  Content-Type: application/pdf
  X-API-Key: <your-api-key>  (required for remote access)"""

        ttk.Label(api_frame, text=api_text, font=("Consolas", 9), justify=tk.LEFT).pack(anchor=tk.W)

        # Separator
        ttk.Separator(center_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)

        # KSI Digital branding
        ttk.Label(center_frame, text="Developed by", font=("Arial", 9), foreground="gray").pack()
        ttk.Label(center_frame, text="KSI Digital", font=("Arial", 16, "bold")).pack(pady=(5, 10))

        # Website link button
        def open_website():
            webbrowser.open("https://ksi-digital.com")

        website_btn = ttk.Button(center_frame, text="Visit ksi-digital.com", command=open_website)
        website_btn.pack(pady=5)

        # Credits (compact)
        credits_text = "PDF printing powered by SumatraPDF  •  Inspired by PrinterOne"
        ttk.Label(center_frame, text=credits_text,
                  font=("Arial", 8), foreground="gray").pack(pady=(15, 5))

        # Copyright
        ttk.Label(center_frame, text="Copyright (c) 2025 KSI Digital. All rights reserved.",
                  font=("Arial", 8), foreground="gray").pack(pady=(10, 10))

    def log_message(self, message):
        """Add message to server log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()

        if hasattr(self, 'logger'):
            self.logger.info(message)

        # Limit log size
        if int(self.log_text.index('end-1c').split('.')[0]) > 1000:
            self.log_text.delete('1.0', '100.0')

    def log_test_message(self, message):
        """Add message to test log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        self.test_log_text.insert(tk.END, log_entry)
        self.test_log_text.see(tk.END)
        self.test_log_text.update_idletasks()

        if int(self.test_log_text.index('end-1c').split('.')[0]) > 100:
            self.test_log_text.delete('1.0', '10.0')

    def save_configuration(self):
        """Save configuration"""
        printer_name = self.printer_var.get()
        port = self.port_var.get()

        if not printer_name:
            self.log_message("[WARN] Please select a printer!")
            return

        if self.server.save_config(printer_name=printer_name, port=port):
            self.log_message("[OK] Configuration saved!")

        if self.test_port_var.get() == 8080:
            self.test_port_var.set(port)

    def start_server(self):
        """Start the server"""
        if self.server_thread and self.server_thread.is_alive():
            self.log_message("[WARN] Server already running!")
            return

        printer_name = self.printer_var.get()
        port = self.port_var.get()

        if not printer_name:
            self.log_message("[WARN] Please select a printer!")
            return

        self.server.save_config(printer_name=printer_name, port=port)

        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()

        self.log_message("[START] Starting server...")
        self.root.after(1000, self.update_server_status)

    def stop_server(self):
        """Stop the server"""
        self.server.stop()
        self.log_message("[STOP] Server stopped")
        self.update_server_status()

    def auto_start_server(self):
        """Auto-start server"""
        printer_name = self.server.config.get("printer_name", "")
        if printer_name:
            self.log_message("[AUTO] Auto-starting server...")
            self.start_server()
        else:
            self.log_message("[INFO] No printer configured")

    def update_status(self):
        """Update all status displays"""
        self.update_server_status()

    def update_server_status(self):
        """Update server status"""
        if self.server.running:
            self.server_dot_label.config(fg="green")
            self.server_status_label.config(text=" Server Running")
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.copy_url_btn.config(state="normal")
            # Disable config editing while running
            self.printer_combo.config(state="disabled")
            self.port_entry.config(state="disabled")
            self.save_config_btn.config(state="disabled")
            self.tunnel_check.config(state="disabled")

            port = self.server.config.get("port", 8080)
            local_ip = self.server.get_local_ip()
            self.server_url = f"http://{local_ip}:{port}"

            # Check for tunnel URL - show only tunnel URL if active
            tunnel_url = self.server.tunnel.get_url()
            if tunnel_url:
                self.server_info_label.config(text=tunnel_url)
                self.tunnel_url = tunnel_url
                # Show API key when tunnel is active (right below URL)
                self.api_key_display_frame.pack(pady=(0, 5))
                # Update test client to use tunnel URL and API key
                self.test_url_var.set(tunnel_url)
                self.test_api_key_var.set(self.server.config.get('api_key', ''))
            else:
                self.server_info_label.config(text=self.server_url)
                self.tunnel_url = None
                # Hide API key display
                self.api_key_display_frame.pack_forget()
                # Update test client to use local (no API key needed)
                self.test_url_var.set(f"http://localhost:{port}")
                self.test_api_key_var.set("")
        else:
            self.server_dot_label.config(fg="red")
            self.server_status_label.config(text=" Server Stopped")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.copy_url_btn.config(state="disabled")
            # Enable config editing when stopped
            self.printer_combo.config(state="readonly")
            self.port_entry.config(state="normal")
            self.save_config_btn.config(state="normal")
            self.tunnel_check.config(state="normal")
            self.server_info_label.config(text="")
            self.server_url = None
            self.tunnel_url = None
            # Hide API key display
            self.api_key_display_frame.pack_forget()


    def test_connection(self):
        """Test connection"""
        base_url = self.test_url_var.get().rstrip('/')
        api_key = self.test_api_key_var.get() or None

        self.log_test_message(f"Testing connection to {base_url}...")

        def run_test():
            test_client.test_connection(base_url, api_key=api_key, log_callback=self.log_test_message)

        threading.Thread(target=run_test, daemon=True).start()

    def send_blank_pdf(self):
        """Send blank test PDF to server"""
        base_url = self.test_url_var.get().rstrip('/')
        api_key = self.test_api_key_var.get() or None

        # Find blank.pdf - check PyInstaller bundle first, then assets folder
        if hasattr(sys, '_MEIPASS'):
            blank_pdf = os.path.join(sys._MEIPASS, 'blank.pdf')
        else:
            package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            blank_pdf = os.path.join(package_dir, 'assets', 'blank.pdf')

        if not os.path.exists(blank_pdf):
            self.log_test_message(f"[ERROR] blank.pdf not found")
            return

        self.log_test_message("Sending blank.pdf...")

        def run_send():
            test_client.send_pdf_file(base_url, blank_pdf, api_key=api_key, log_callback=self.log_test_message)

        threading.Thread(target=run_send, daemon=True).start()

    def send_selected_pdf(self):
        """Let user select a PDF file to print locally (tests print settings)"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if not file_path:
            return

        self.log_test_message(f"Printing: {os.path.basename(file_path)}")

        # Print locally using current settings
        printer_name = self.server.config.get("printer_name", "")
        if not printer_name:
            self.log_test_message("[ERROR] No printer configured")
            return

        def run_print():
            from . import printer as prn
            try:
                with open(file_path, 'rb') as f:
                    pdf_data = f.read()
                success = prn.print_pdf(pdf_data, printer_name, self.log_test_message, self.server.config)
                if success:
                    self.log_test_message("[OK] Print job completed")
            except Exception as e:
                self.log_test_message(f"[ERROR] {e}")

        threading.Thread(target=run_print, daemon=True).start()

    def start_status_thread(self):
        """Start status update thread"""
        def updater():
            while True:
                try:
                    self.root.after(0, self.update_server_status)
                    time.sleep(2)
                except:
                    break

        threading.Thread(target=updater, daemon=True).start()

    def on_minimize_option_changed(self):
        """Handle minimize option change"""
        self.minimize_to_tray = self.minimize_to_tray_var.get()
        self.server.save_config(minimize_to_tray=self.minimize_to_tray)

    def on_autostart_changed(self):
        """Handle auto-start checkbox change"""
        if self.autostart_var.get():
            success, message = autostart.add_to_startup()
        else:
            success, message = autostart.remove_from_startup()
        self.log_message(f"[{'OK' if success else 'ERROR'}] {message}")

    def copy_server_url(self):
        """Copy server URL to clipboard (prefers tunnel URL if available)"""
        # Prefer tunnel URL for remote access
        url_to_copy = None
        if hasattr(self, 'tunnel_url') and self.tunnel_url:
            url_to_copy = self.tunnel_url
        elif hasattr(self, 'server_url') and self.server_url:
            url_to_copy = self.server_url

        if url_to_copy:
            self.root.clipboard_clear()
            self.root.clipboard_append(url_to_copy)
            self.log_message(f"[OK] Copied: {url_to_copy}")

    def on_tunnel_setting_changed(self):
        """Handle tunnel setting change"""
        use_tunnel = self.use_tunnel_var.get()

        # Generate API key if enabling tunnel and no key exists
        if use_tunnel and not self.server.config.get('api_key'):
            new_key = cfg.generate_api_key()
            self.server.save_config(use_tunnel=use_tunnel, api_key=new_key)
            self.api_key_var.set(new_key)
        else:
            self.server.save_config(use_tunnel=use_tunnel)

        self.log_message(f"[OK] Remote access {'enabled' if use_tunnel else 'disabled'} (restart server to apply)")

    def copy_api_key(self):
        """Copy API key to clipboard"""
        api_key = self.api_key_var.get()
        if api_key:
            self.root.clipboard_clear()
            self.root.clipboard_append(api_key)
            self.log_message(f"[OK] API key copied to clipboard")

    def regenerate_api_key(self):
        """Regenerate API key"""
        new_key = cfg.generate_api_key()
        self.server.save_config(api_key=new_key)
        self.api_key_var.set(new_key)
        self.log_message(f"[OK] New API key generated")

    def on_print_settings_changed(self, event=None):
        """Handle print settings change"""
        # Convert display values back to config keys
        scaling_display = self.scaling_combo.get()
        color_display = self.color_combo.get()
        duplex_display = self.duplex_combo.get()

        # Reverse lookup
        scaling_key = next((k for k, v in cfg.SCALING_OPTIONS.items() if v == scaling_display), "shrink")
        color_key = next((k for k, v in cfg.COLOR_OPTIONS.items() if v == color_display), "color")
        duplex_key = next((k for k, v in cfg.DUPLEX_OPTIONS.items() if v == duplex_display), "simplex")

        self.server.save_config(
            print_scaling=scaling_key,
            print_color=color_key,
            print_duplex=duplex_key
        )
        self.log_message(f"[OK] Print settings saved")

    def update_sumatra(self):
        """Update SumatraPDF to latest version"""
        if self.server.running:
            self.log_message("[WARN] Please stop the server before updating SumatraPDF")
            return

        self.log_message("[UPDATE] Updating SumatraPDF...")

        def run_update():
            result = sumatra.download_sumatra(log_callback=self.log_message, force_update=True)
            if result:
                self.log_message("[OK] SumatraPDF update completed")
            else:
                self.log_message("[ERROR] SumatraPDF update failed")

        threading.Thread(target=run_update, daemon=True).start()

    def update_cloudflared(self):
        """Update Cloudflare Tunnel to latest version"""
        if self.server.running:
            self.log_message("[WARN] Please stop the server before updating Cloudflare Tunnel")
            return

        self.log_message("[UPDATE] Updating Cloudflare Tunnel...")

        def run_update():
            result = tunnel.download_cloudflared(log_callback=self.log_message, force_update=True)
            if result:
                self.log_message("[OK] Cloudflare Tunnel update completed")
            else:
                self.log_message("[ERROR] Cloudflare Tunnel update failed")

        threading.Thread(target=run_update, daemon=True).start()

    def on_closing(self):
        """Handle window closing"""
        if TRAY_AVAILABLE and self.tray_icon and self.minimize_to_tray:
            self.hide_window()
        else:
            self.quit_app()

    def quit_app(self):
        """Quit application"""
        self.log_message("[BYE] Shutting down...")

        if self.server.running:
            self.server.stop()
            time.sleep(1)

        if TRAY_AVAILABLE and self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass

        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def setup_tray(self):
        """Setup system tray"""
        if not TRAY_AVAILABLE:
            return

        try:
            # Load icon from file
            if hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                icon_path = os.path.join(script_dir, 'assets', 'icon.ico')

            if os.path.exists(icon_path):
                tray_image = Image.open(icon_path)
            else:
                tray_image = Image.new('RGB', (64, 64), color='#4a5568')

            menu = pystray.Menu(
                pystray.MenuItem("Show Window", self.show_window, default=True),
                pystray.MenuItem("Hide Window", self.hide_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Start Server", lambda: self.root.after(0, self.start_server)),
                pystray.MenuItem("Stop Server", lambda: self.root.after(0, self.stop_server)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self.quit_app)
            )

            self.tray_icon = pystray.Icon("AutomaPrint", tray_image, "AutomaPrint Server", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

        except Exception as e:
            self.log_message(f"[WARN] Tray setup failed: {e}")

    def show_window(self, icon=None, item=None):
        """Show window from tray"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self, icon=None, item=None):
        """Hide window to tray"""
        self.root.withdraw()


def run_gui(auto_start_mode=False):
    """Run the GUI application"""
    root = tk.Tk()
    app = AutomaPrintGUI(root, auto_start_mode)
    root.mainloop()
