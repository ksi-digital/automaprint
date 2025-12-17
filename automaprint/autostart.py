"""
Windows auto-start management for AutomaPrint
"""

import os
import sys
import winreg


def get_startup_command():
    """Get the command to run AutomaPrint at startup"""
    if hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller exe
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}" gui auto_start'
    else:
        # Running from Python script
        # Find the main.py in the package directory
        package_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(os.path.dirname(package_dir), 'main.py')
        python_exe = os.path.abspath(sys.executable)
        return f'"{python_exe}" "{main_script}" gui auto_start'


def add_to_startup():
    """Add AutomaPrint to Windows startup"""
    try:
        command = get_startup_command()

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )

        winreg.SetValueEx(key, "AutomaPrint", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)

        return True, "AutomaPrint added to Windows startup!"

    except Exception as e:
        return False, f"Error adding to startup: {e}"


def remove_from_startup():
    """Remove AutomaPrint from Windows startup"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )

        winreg.DeleteValue(key, "AutomaPrint")
        winreg.CloseKey(key)

        return True, "AutomaPrint removed from Windows startup!"

    except FileNotFoundError:
        return True, "AutomaPrint was not in startup"
    except Exception as e:
        return False, f"Error removing from startup: {e}"


def check_startup_status():
    """Check if AutomaPrint is in startup"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )

        try:
            value, _ = winreg.QueryValueEx(key, "AutomaPrint")
            winreg.CloseKey(key)
            return True, value
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False, "Not in startup"

    except Exception as e:
        return False, f"Error checking startup: {e}"
