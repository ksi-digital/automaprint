#!/usr/bin/env python3
"""
AutomaPrint Server - REST API PDF Print Server

A simple REST API server that receives PDF files and prints them to a local printer.

Usage:
    python main.py              - Run GUI (default)
    python main.py gui          - Run GUI
    python main.py gui auto_start - Run GUI minimized with auto-start
    python main.py server       - Run server only (no GUI)
    python main.py test         - Run test client
    python main.py --help       - Show help
"""

import sys
import signal


def signal_handler(signum, frame):
    """Handle Ctrl+C"""
    print("\n[STOP] Shutting down...")
    sys.exit(0)


def run_server_only():
    """Run server without GUI"""
    from automaprint.server import PrintServer

    print("AutomaPrint Server - REST API PDF Print Server")
    print("=" * 46)
    print()

    server = PrintServer()

    if not server.config.get("printer_name"):
        print("No printer configured!")
        print()

        printers = server.list_printers()
        if not printers:
            print("[!] No printers found!")
            return

        print("Available printers:")
        for i, printer in enumerate(printers, 1):
            print(f"  {i}. {printer}")

        while True:
            try:
                selection = input(f"\nSelect printer (1-{len(printers)}): ")
                idx = int(selection) - 1
                if 0 <= idx < len(printers):
                    selected = printers[idx]
                    break
            except ValueError:
                pass
            print("[!] Invalid selection")

        port_input = input("Port (default 8080): ").strip()
        port = int(port_input) if port_input else 8080

        server.save_config(printer_name=selected, port=port)
        print("[OK] Configuration saved")

    print(f"Starting server...")
    print(f"Printer: {server.config['printer_name']}")
    print(f"Port: {server.config['port']}")
    print("Press Ctrl+C to stop")
    print()

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[STOP] Server stopped")


def run_test_client():
    """Run interactive test client"""
    from automaprint import test_client

    print("AutomaPrint Server - Test Client")
    print("=" * 33)
    print()

    host = input("Server host (localhost): ").strip() or "localhost"
    port_input = input("Server port (8080): ").strip()
    port = int(port_input) if port_input else 8080

    print()
    print("1. Test connection")
    print("2. Send PDF file")
    print()

    choice = input("Choice (1-2): ").strip()

    if choice == "1":
        test_client.test_connection(host, port)
    elif choice == "2":
        pdf_path = input("PDF file path: ").strip()
        test_client.send_pdf_file(host, port, pdf_path)
    else:
        print("Invalid choice")


def show_help():
    """Show help"""
    print(__doc__)
    print()
    print("REST API Endpoints:")
    print("  GET  /health - Health check")
    print("  POST /print  - Print PDF file (body = PDF data)")
    print()
    print("Example (curl):")
    print('  curl -X POST -H "Content-Type: application/pdf" \\')
    print('       --data-binary @document.pdf http://localhost:8080/print')
    print()


def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, signal_handler)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command in ['--help', '-h', 'help']:
            show_help()
        elif command == 'gui':
            auto_start = 'auto_start' in sys.argv
            from automaprint.gui import run_gui
            run_gui(auto_start)
        elif command == 'server':
            run_server_only()
        elif command == 'test':
            run_test_client()
        else:
            print(f"Unknown command: {command}")
            show_help()
    else:
        # Default to GUI
        try:
            from automaprint.gui import run_gui
            run_gui()
        except ImportError as e:
            print(f"GUI dependencies not available: {e}")
            print("Running in server mode...")
            run_server_only()


if __name__ == "__main__":
    main()
