# AutomaPrint

**REST API Print Server for Windows**

AutomaPrint is a lightweight Windows application that provides a REST API for printing PDF files to local printers. It includes a GUI for easy configuration and optional Cloudflare tunnel support for remote access.

## Features

- 🖨️ **REST API** - Simple HTTP endpoint for printing PDFs
- 🖥️ **GUI Interface** - Easy-to-use system tray application
- ⚙️ **Print Settings** - Configure scaling, color mode, and duplex printing
- 🌐 **Remote Access** - Built-in Cloudflare tunnel for remote printing
- 🔧 **Auto-download** - Automatically downloads dependencies (SumatraPDF) on first use
- 🚀 **Zero Config** - Works out of the box with sensible defaults

## Installation

### Download Pre-built Release

1. Download `AutomaPrint.exe` from the [latest release](https://github.com/ksi-digital/automaprint/releases)
2. Run the executable
3. Select your printer from the list
4. That's it! The server will start automatically

### Build from Source

Requirements:
- Python 3.11+
- Windows OS

```bash
# Clone the repository
git clone https://github.com/ksi-digital/automaprint.git
cd automaprint

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

### GUI Mode (Default)

Simply run the executable or:

```bash
python main.py
```

The application will:
- Start in the system tray
- Auto-start the print server
- Show status and tunnel information (if enabled)

### Server-Only Mode

Run without GUI:

```bash
python main.py server
```

### Test Client

Test your installation:

```bash
python main.py test
```

## API Reference

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "printer": "HP LaserJet Pro",
  "version": "1.0.0"
}
```

### Print PDF

```bash
POST /print
Content-Type: application/pdf
```

**Example:**

```bash
# Print a PDF file
curl -X POST -H "Content-Type: application/pdf" \
     --data-binary @document.pdf \
     http://localhost:8080/print
```

**Response:**
```json
{
  "status": "success",
  "message": "Print job sent successfully"
}
```

### Using with API Key (Remote Access)

When Cloudflare tunnel is enabled, use the API key for authentication:

```bash
curl -X POST -H "Content-Type: application/pdf" \
     -H "X-API-Key: your-api-key-here" \
     --data-binary @document.pdf \
     https://your-tunnel-url.trycloudflare.com/print
```

## Configuration

Configuration is stored in `%USERPROFILE%\AutomaPrint\config.json`

**Default Settings:**

```json
{
  "printer_name": "",
  "port": 8080,
  "auto_start": false,
  "minimize_to_tray": true,
  "print_scaling": "shrink",
  "print_color": "color",
  "print_duplex": "simplex",
  "use_tunnel": false,
  "api_key": ""
}
```

### Print Settings

| Setting | Options | Description |
|---------|---------|-------------|
| `print_scaling` | `fit`, `shrink`, `noscale` | How to scale pages to fit paper |
| `print_color` | `color`, `monochrome` | Color or black & white printing |
| `print_duplex` | `simplex`, `duplexlong`, `duplexshort` | Single or double-sided printing |

### Remote Access (Cloudflare Tunnel)

Enable remote access via the GUI settings:

1. Check "Enable Cloudflare Tunnel"
2. Start the server
3. Copy the tunnel URL shown in the status
4. Use the displayed API key for authentication

**Security:** API keys are automatically generated and required for all requests when tunnel is enabled.

## Build Executable

Build a standalone executable using PyInstaller:

```bash
python build.py
```

The executable will be created in `dist/AutomaPrint.exe`

## Architecture

```
┌─────────────────────────────────────────┐
│  AutomaPrint GUI (System Tray)          │
│  - Configuration                         │
│  - Status Display                        │
│  - Tunnel Management                     │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  Flask REST API Server                  │
│  - /health  - Health check              │
│  - /print   - Print PDF                 │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  Print Engine                            │
│  - SumatraPDF (auto-downloaded)         │
│  - Win32 Print API                       │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│  Windows Print Spooler                   │
│  → Local Printer                         │
└──────────────────────────────────────────┘

Optional:
┌─────────────────────────────────────────┐
│  Cloudflare Tunnel (cloudflared)        │
│  - Auto-download on enable              │
│  - Public HTTPS endpoint                 │
│  - API key authentication                │
└──────────────────────────────────────────┘
```

## Dependencies

### Runtime (Auto-downloaded)
- **SumatraPDF** - PDF rendering and printing (downloaded on first use)
- **cloudflared** - Cloudflare tunnel client (downloaded when tunnel is enabled)

### Python Dependencies
- Flask - Web framework
- pywin32 - Windows API access
- pystray - System tray icon
- Pillow - Image processing

See [requirements.txt](requirements.txt) for full list.

## Use Cases

- **Automated Printing** - Integrate printing into workflows and scripts
- **Remote Printing** - Print from anywhere via Cloudflare tunnel
- **Label Printing** - Print shipping labels from web applications
- **Document Automation** - Auto-print invoices, receipts, reports
- **IoT Printing** - Enable printing from embedded devices

## Troubleshooting

### Port Already in Use

Change the port in configuration or via GUI settings.

### Printer Not Found

1. Ensure printer is installed and online
2. Check printer name matches exactly (case-sensitive)
3. Restart the application

### PDF Not Printing

1. Check PDF file is valid
2. Verify SumatraPDF downloaded successfully (check `%USERPROFILE%\AutomaPrint\`)
3. Test with blank.pdf from assets folder

### Firewall Issues

Add exception for AutomaPrint in Windows Firewall:
```
Control Panel → Windows Defender Firewall → Allow an app
```

## Security Notes

- **Local Mode**: No authentication required (localhost only)
- **Tunnel Mode**: API key required for all requests
- **API Keys**: Auto-generated UUIDs, stored in config.json
- **HTTPS**: Cloudflare tunnel provides automatic HTTPS

**Recommendation:** Only enable tunnel mode when needed, and regenerate API keys regularly via the GUI.

## Development

### Project Structure

```
automaprint/
├── automaprint/          # Main package
│   ├── config.py         # Configuration management
│   ├── server.py         # Flask REST API
│   ├── printer.py        # Print engine
│   ├── sumatra.py        # SumatraPDF download manager
│   ├── tunnel.py         # Cloudflare tunnel manager
│   ├── gui.py            # GUI application
│   ├── autostart.py      # Windows autostart
│   └── test_client.py    # Test utilities
├── assets/               # Icons and test files
├── main.py               # Entry point
├── build.py              # PyInstaller build script
├── AutomaPrint.spec      # PyInstaller configuration
└── requirements.txt      # Python dependencies
```

### Running Tests

```bash
# Start test client
python main.py test

# Manual API test
curl http://localhost:8080/health
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- 🐛 [Report Issues](https://github.com/ksi-digital/automaprint/issues)
- 💬 [Discussions](https://github.com/ksi-digital/automaprint/discussions)

## Author

**KSI Digital**
- Website: [ksi-digital.com](https://ksi-digital.com)
- GitHub: [@ksi-digital](https://github.com/ksi-digital)

## Acknowledgments

- [SumatraPDF](https://www.sumatrapdfreader.org/) - Fast, lightweight PDF viewer
- [Cloudflare](https://www.cloudflare.com/) - Cloudflare Tunnel for remote access
