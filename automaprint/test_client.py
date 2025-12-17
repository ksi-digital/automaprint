"""
Test client for AutomaPrint REST API
"""

import urllib.request
import urllib.error
import urllib.parse
import json
import ssl


def _get_ssl_context(url):
    """Get SSL context - verify certs for HTTPS, skip for local HTTP"""
    ctx = ssl.create_default_context()
    # Only skip verification for non-HTTPS (local testing)
    if not url.startswith('https://'):
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def test_connection(base_url, api_key=None, log_callback=None):
    """Test connection to print server

    Args:
        base_url: Full URL like "http://localhost:8080" or "https://xyz.trycloudflare.com"
        api_key: Optional API key for authenticated requests
        log_callback: Optional logging function
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    try:
        url = f"{base_url.rstrip('/')}/health"
        log(f"[CONNECT] Testing connection to {url}...")

        req = urllib.request.Request(url)
        if api_key:
            req.add_header('X-API-Key', api_key)

        ctx = _get_ssl_context(url)

        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            data = response.read().decode('utf-8')
            log(f"[OK] Server is running!")
            log(f"[INFO] Response: {data}")

        return True

    except urllib.error.URLError as e:
        log(f"[ERROR] Connection failed: {e.reason}")
        return False
    except Exception as e:
        log(f"[ERROR] Error: {e}")
        return False


def send_pdf(base_url, pdf_data, printer=None, api_key=None, log_callback=None):
    """Send PDF data to print server

    Args:
        base_url: Full URL like "http://localhost:8080" or "https://xyz.trycloudflare.com"
        pdf_data: PDF file bytes
        printer: Optional printer name override
        api_key: Optional API key for authenticated requests
        log_callback: Optional logging function
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    try:
        url = f"{base_url.rstrip('/')}/print"
        if printer:
            url += f"?printer={urllib.parse.quote(printer)}"

        log(f"[SEND] Sending {len(pdf_data)} bytes to {url}...")

        headers = {'Content-Type': 'application/pdf'}
        if api_key:
            headers['X-API-Key'] = api_key

        req = urllib.request.Request(url, data=pdf_data, headers=headers)
        ctx = _get_ssl_context(url)

        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            result = json.loads(response.read().decode('utf-8'))
            log(f"[OK] Print job sent!")
            log(f"[INFO] Response: {json.dumps(result)}")

        return True

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        log(f"[ERROR] HTTP {e.code}: {error_body}")
        return False
    except urllib.error.URLError as e:
        log(f"[ERROR] Connection failed: {e.reason}")
        return False
    except Exception as e:
        log(f"[ERROR] Error: {e}")
        return False


def send_pdf_file(base_url, pdf_path, printer=None, api_key=None, log_callback=None):
    """Send a PDF file to the print server

    Args:
        base_url: Full URL like "http://localhost:8080" or "https://xyz.trycloudflare.com"
        pdf_path: Path to PDF file
        printer: Optional printer name override
        api_key: Optional API key for authenticated requests
        log_callback: Optional logging function
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    try:
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()

        log(f"[FILE] Loaded {pdf_path} ({len(pdf_data)} bytes)")

        # Validate it's a PDF
        if not pdf_data[:4] == b'%PDF':
            log(f"[ERROR] File is not a valid PDF")
            return False

        return send_pdf(base_url, pdf_data, printer, api_key, log_callback)

    except FileNotFoundError:
        log(f"[ERROR] File not found: {pdf_path}")
        return False
    except Exception as e:
        log(f"[ERROR] Error: {e}")
        return False
