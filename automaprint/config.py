"""
Configuration management for AutomaPrint
"""

import os
import json
import uuid


DEFAULT_CONFIG = {
    "printer_name": "",
    "port": 8080,
    "auto_start": False,
    "minimize_to_tray": True,
    "service_name": "AutomaPrint",
    "service_description": "AutomaPrint Server - REST API print server for PDF files",
    # Print settings
    "print_scaling": "shrink",      # fit, shrink, noscale
    "print_color": "color",         # color, monochrome
    "print_duplex": "simplex",      # simplex, duplexlong, duplexshort
    # Tunnel settings
    "use_tunnel": False,            # Enable Cloudflare tunnel for remote access
    "api_key": "",                  # API key for remote access (auto-generated)
}


def generate_api_key():
    """Generate a new API key"""
    return str(uuid.uuid4())

# Display labels for print settings
SCALING_OPTIONS = {
    "fit": "Fit to Page",
    "shrink": "Shrink Only",
    "noscale": "Original Size (100%)",
}

COLOR_OPTIONS = {
    "color": "Color",
    "monochrome": "Monochrome",
}

DUPLEX_OPTIONS = {
    "simplex": "Single-sided",
    "duplexlong": "Double-sided (Long Edge)",
    "duplexshort": "Double-sided (Short Edge)",
}


def get_data_dir():
    """Get the application data directory"""
    data_dir = os.path.join(os.path.expanduser('~'), 'AutomaPrint')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_config_paths():
    """Get list of possible config file locations"""
    return [
        os.path.join(get_data_dir(), 'config.json'),
        'config.json',  # Current working directory fallback
    ]


def load_config(logger=None):
    """Load configuration from config.json"""
    config_path = None

    for path in get_config_paths():
        try:
            path = os.path.abspath(path)
            if logger:
                logger.info(f"Trying to load configuration from: {path}")

            if os.path.exists(path):
                with open(path, 'r') as f:
                    config = json.load(f)

                # Merge with defaults
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value

                if logger:
                    logger.info(f"Config loaded from: {path}")

                return config, path

        except PermissionError:
            if logger:
                logger.warning(f"Permission denied: {path}")
            continue
        except Exception as e:
            if logger:
                logger.warning(f"Error loading from {path}: {e}")
            continue

    # No config found, return defaults with path to user folder
    if logger:
        logger.info("Using default configuration")

    return DEFAULT_CONFIG.copy(), os.path.join(get_data_dir(), 'config.json')


def save_config(config, config_path=None, logger=None):
    """Save configuration to config.json"""
    paths_to_try = []

    if config_path:
        paths_to_try.append(config_path)

    paths_to_try.extend(get_config_paths())

    for path in paths_to_try:
        try:
            config_dir = os.path.dirname(path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(path, 'w') as f:
                json.dump(config, f, indent=4)

            if logger:
                logger.info(f"Configuration saved to {path}")

            return True, path

        except PermissionError:
            if logger:
                logger.warning(f"Permission denied saving to {path}")
            continue
        except Exception as e:
            if logger:
                logger.warning(f"Error saving to {path}: {e}")
            continue

    if logger:
        logger.error("Failed to save configuration to any location")

    return False, None
