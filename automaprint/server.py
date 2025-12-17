"""
REST API Server for AutomaPrint
"""

import socket
import psutil
import time

from flask import Flask, request, jsonify
from werkzeug.serving import make_server

from . import printer
from . import config as cfg
from .tunnel import TunnelManager


class PrintServer:
    """REST API Print Server"""

    def __init__(self, log_callback=None):
        self.config, self.config_path = cfg.load_config()
        self.http_server = None
        self.flask_app = None
        self.running = False
        self.log_callback = log_callback
        self.tunnel = TunnelManager(log_callback)

        # Ensure API key exists if tunnel is enabled
        if self.config.get('use_tunnel') and not self.config.get('api_key'):
            self.config['api_key'] = cfg.generate_api_key()
            cfg.save_config(self.config, self.config_path)

    def log(self, message):
        """Log message to console and callback"""
        print(message)
        if self.log_callback:
            # Clean up message for GUI
            clean_message = message
            if message.startswith("[") and "]" in message:
                bracket_end = message.find("]")
                if bracket_end != -1:
                    clean_message = message[bracket_end + 1:].strip()
            self.log_callback(clean_message)

    def save_config(self, **kwargs):
        """Save configuration"""
        for key, value in kwargs.items():
            if value is not None:
                self.config[key] = value

        success, path = cfg.save_config(self.config, self.config_path)
        if success:
            self.config_path = path
            self.log(f"[SAVE] Configuration saved to {path}")
        else:
            self.log("[!] Failed to save configuration")
        return success

    def list_printers(self):
        """List available printers"""
        return printer.list_printers()

    def create_flask_app(self):
        """Create Flask application with REST API endpoints"""
        app = Flask(__name__)

        # CORS headers for browser requests
        @app.after_request
        def add_cors_headers(response):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
            return response

        def check_api_key():
            """Check API key if tunnel is enabled"""
            if not self.config.get('use_tunnel'):
                return True  # No auth needed for local access

            api_key = self.config.get('api_key', '')
            if not api_key:
                return True  # No key configured

            request_key = request.headers.get('X-API-Key', '')
            return request_key == api_key

        @app.route('/health', methods=['GET', 'OPTIONS'])
        def health():
            """Health check endpoint"""
            # Handle preflight request
            if request.method == 'OPTIONS':
                return '', 204

            # Check API key for tunnel access
            if not check_api_key():
                self.log("[!] Unauthorized: Invalid API key")
                return jsonify({'error': 'Unauthorized: Invalid API key'}), 401

            return jsonify({
                'status': 'ok',
                'printer': self.config.get('printer_name', ''),
                'port': self.config.get('port', 8080)
            })

        @app.route('/print', methods=['POST', 'OPTIONS'])
        def print_pdf_endpoint():
            """Print PDF file endpoint"""
            # Handle preflight request
            if request.method == 'OPTIONS':
                return '', 204

            # Check API key for tunnel access
            if not check_api_key():
                self.log("[!] Unauthorized: Invalid API key")
                return jsonify({'error': 'Unauthorized: Invalid API key'}), 401

            try:
                printer_name = request.args.get('printer', self.config.get('printer_name', ''))

                if not printer_name:
                    self.log("[!] No printer specified")
                    return jsonify({'error': 'No printer specified'}), 400

                # Get PDF data
                if 'file' in request.files:
                    pdf_file = request.files['file']
                    pdf_data = pdf_file.read()
                    filename = pdf_file.filename or 'unknown.pdf'
                    self.log(f"[API] Received file upload: {filename}")
                else:
                    pdf_data = request.get_data()
                    self.log("[API] Received raw PDF data")

                if not pdf_data:
                    self.log("[!] No PDF data received")
                    return jsonify({'error': 'No PDF data received'}), 400

                self.log(f"[API] Received {len(pdf_data)} bytes")

                # Validate PDF
                if not printer.is_pdf(pdf_data):
                    self.log("[!] Data is not a valid PDF")
                    return jsonify({'error': 'Data is not a valid PDF file'}), 400

                # Print with settings from config
                self.log(f"[API] Printing to: {printer_name}")
                success = printer.print_pdf(pdf_data, printer_name, self.log, self.config)

                if success:
                    self.log("[OK] Print job sent successfully")
                    return jsonify({
                        'success': True,
                        'message': 'Print job sent successfully',
                        'printer': printer_name,
                        'bytes': len(pdf_data)
                    })
                else:
                    self.log("[!] Print job failed")
                    return jsonify({'error': 'Print job failed'}), 500

            except Exception as e:
                self.log(f"[!] API error: {e}")
                return jsonify({'error': str(e)}), 500

        return app

    def get_local_ip(self):
        """Get the local IP address"""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                test_socket.connect(("8.8.8.8", 80))
                local_ip = test_socket.getsockname()[0]
                test_socket.close()

                if not local_ip.startswith('127.') and not local_ip.startswith('169.254.'):
                    return local_ip
            except:
                test_socket.close()

            # Fallback to psutil
            for interface_name, interface_addresses in psutil.net_if_addrs().items():
                if any(skip in interface_name.lower() for skip in ['virtualbox', 'vmware', 'loopback']):
                    continue

                for address in interface_addresses:
                    if address.family == socket.AF_INET:
                        ip = address.address
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            return ip

            return '127.0.0.1'

        except Exception:
            return '127.0.0.1'

    def kill_process_on_port(self, port):
        """Kill any process using the specified port"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    try:
                        process = psutil.Process(conn.pid)
                        process.terminate()
                        self.log(f"[KILL] Terminated process {conn.pid} using port {port}")
                        time.sleep(1)

                        if process.is_running():
                            process.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        except Exception as e:
            self.log(f"[!] Error killing process on port {port}: {e}")

    def start(self):
        """Start the REST API server"""
        printer_name = self.config.get("printer_name", "")
        port = self.config.get("port", 8080)
        use_tunnel = self.config.get("use_tunnel", False)

        if not printer_name:
            self.log("[!] No printer configured!")
            return False

        self.log(f"[KILL] Checking for processes using port {port}...")
        self.kill_process_on_port(port)

        try:
            self.flask_app = self.create_flask_app()
            self.http_server = make_server('0.0.0.0', port, self.flask_app, threaded=True)
            self.running = True

            self.log(f"[OK] REST API Server started on port {port}")
            self.log(f"[PRINTER] Using printer: {printer_name}")

            local_ip = self.get_local_ip()
            self.log(f"[IP] Local IP: {local_ip}")
            self.log(f"[API] Endpoints:")
            self.log(f"      GET  http://{local_ip}:{port}/health")
            self.log(f"      POST http://{local_ip}:{port}/print")

            # Start tunnel if enabled
            if use_tunnel:
                self.tunnel.start(port)

            self.http_server.serve_forever()

        except Exception as e:
            self.log(f"[!] Server error: {e}")
            return False
        finally:
            self.stop()

        return True

    def stop(self):
        """Stop the REST API server"""
        self.running = False

        # Stop tunnel if running
        if self.tunnel.running:
            self.tunnel.stop()

        if self.http_server:
            try:
                self.http_server.shutdown()
            except:
                pass
            self.http_server = None

        self.log("[DONE] Server stopped")
