"""
PDF and raw printing utilities for AutomaPrint
"""

import os
import time
import tempfile
import threading
import subprocess

import win32print


def list_printers():
    """List all available printers"""
    try:
        printers = []
        for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL, None, 1):
            printers.append(printer[2])
        return printers
    except Exception as e:
        print(f"[!] Error listing printers: {e}")
        return []


def is_pdf(data):
    """Check if data is a PDF file"""
    return len(data) >= 4 and data[:4] == b'%PDF'


def print_raw(data, printer_name, log_callback=None):
    """Send raw data to printer"""
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    try:
        log(f"[INFO] Opening printer: {printer_name}")
        hPrinter = win32print.OpenPrinter(printer_name)

        job_info = ("RAW Print Job", None, "RAW")
        hJob = win32print.StartDocPrinter(hPrinter, 1, job_info)
        win32print.StartPagePrinter(hPrinter)
        win32print.WritePrinter(hPrinter, data)
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
        win32print.ClosePrinter(hPrinter)

        log(f"[OK] Successfully printed {len(data)} bytes.")
        return True
    except Exception as e:
        log(f"[!] Print error: {e}")
        return False


def get_sumatra_path():
    """Find SumatraPDF executable (auto-downloads if needed)"""
    from . import sumatra

    # Try to find existing installation
    sumatra_path = sumatra.get_sumatra_path()

    if sumatra_path:
        return sumatra_path

    # Not found, attempt to download
    print("[INFO] SumatraPDF not found, attempting to download...")
    return sumatra.download_sumatra()


def get_sumatra_path_no_download():
    """Find SumatraPDF executable without downloading"""
    from . import sumatra
    return sumatra.get_sumatra_path()


def build_print_settings(scaling="shrink", color="color", duplex="simplex"):
    """Build SumatraPDF print settings string"""
    settings = []

    # Scaling
    if scaling == "noscale":
        settings.append("noscale")
    elif scaling == "shrink":
        settings.append("shrink")
    # "fit" is default, no need to add

    # Color
    if color == "monochrome":
        settings.append("monochrome")
    # "color" is default

    # Duplex
    if duplex == "duplexlong":
        settings.append("duplex")
    elif duplex == "duplexshort":
        settings.append("duplexshort")
    # "simplex" is default

    return ",".join(settings) if settings else None


def print_pdf(pdf_data, printer_name, log_callback=None, print_settings=None):
    """Print PDF using SumatraPDF

    Args:
        pdf_data: PDF file bytes
        printer_name: Target printer name
        log_callback: Optional logging function
        print_settings: Dict with scaling, color, duplex options
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    # Find SumatraPDF
    sumatra = get_sumatra_path()
    if not sumatra:
        log("[!] SumatraPDF not found! Please place SumatraPDF.exe in the app folder.")
        return False

    # Build print settings
    if print_settings:
        settings_str = build_print_settings(
            scaling=print_settings.get("print_scaling", "shrink"),
            color=print_settings.get("print_color", "color"),
            duplex=print_settings.get("print_duplex", "simplex"),
        )
    else:
        settings_str = None

    temp_pdf_path = None
    try:
        # Save PDF to temp file
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf_path = temp_pdf.name
        temp_pdf.write(pdf_data)
        temp_pdf.close()

        log(f"[PDF] Printer: {printer_name}")
        if settings_str:
            log(f"[PDF] Settings: {settings_str}")

        # Build command
        cmd = [sumatra, '-print-to', printer_name]
        if settings_str:
            cmd.extend(['-print-settings', settings_str])
        cmd.extend(['-silent', temp_pdf_path])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            log(f"[OK] Print job sent successfully")
            return True
        else:
            log(f"[!] Print failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        log(f"[OK] Print job sent (process timeout)")
        return True
    except Exception as e:
        log(f"[!] Print error: {e}")
        return False
    finally:
        # Cleanup temp file after delay
        if temp_pdf_path:
            def cleanup():
                time.sleep(10)
                try:
                    os.unlink(temp_pdf_path)
                except:
                    pass
            threading.Thread(target=cleanup, daemon=True).start()


def analyze_data(data):
    """Analyze data to determine format"""
    if len(data) == 0:
        return "Empty data"

    if data.startswith(b'\x1b'):
        return "ESC/P (Epson)"
    elif data.startswith(b'\x1b%-12345X'):
        return "PCL (HP)"
    elif data.startswith(b'%!PS'):
        return "PostScript"
    elif data.startswith(b'\x02'):
        return "ZPL (Zebra)"
    elif data[:4] == b'%PDF':
        return "PDF document"
    else:
        return f"Binary/Unknown ({len(data)} bytes)"
