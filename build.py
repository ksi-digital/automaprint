#!/usr/bin/env python3
"""
Build script for AutomaPrint Server

Creates a minimal size Windows executable using PyInstaller.
Automatically detects installed packages and excludes non-essential ones.

Usage:
    python build.py           - Build the executable
    python build.py --clean   - Clean build artifacts
    python build.py --list    - List packages to exclude
"""

import os
import sys
import shutil
import subprocess
from importlib.metadata import distributions


# Packages that ARE needed for AutomaPrint (whitelist)
REQUIRED_PACKAGES = {
    # Core app
    'flask', 'werkzeug', 'jinja2', 'markupsafe', 'itsdangerous',
    'click', 'blinker', 'colorama',

    # Windows printing
    'win32print', 'win32api', 'win32con', 'win32gui',
    'pywin32', 'pywin32_ctypes', 'pywintypes',

    # System tray & GUI
    'pystray', 'PIL', 'pillow', 'tkinter', 'six',

    # System monitoring
    'psutil',

    # Python stdlib essentials
    'json', 'socket', 'threading', 'time', 'os', 'sys',
    'tempfile', 'logging', 'datetime', 'signal',

    # PyInstaller internals (needed at build time)
    'pyinstaller', 'altgraph', 'pefile', 'packaging',
    'pyinstaller_hooks_contrib', 'setuptools',
}


def get_installed_packages():
    """Get list of installed pip packages using importlib.metadata"""
    packages = set()
    for dist in distributions():
        pkg = dist.metadata['Name'].lower().replace('-', '_')
        packages.add(pkg)
    return packages


def get_exclusions():
    """Get list of packages to exclude (everything not in REQUIRED_PACKAGES)"""
    installed = get_installed_packages()
    required_lower = {p.lower().replace('-', '_') for p in REQUIRED_PACKAGES}

    exclusions = set()
    for pkg in installed:
        if pkg not in required_lower:
            exclusions.add(pkg)

    return sorted(exclusions)


def clean_build():
    """Clean build artifacts"""
    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['AutomaPrint.spec']

    for d in dirs_to_remove:
        if os.path.exists(d):
            print(f"Removing {d}/")
            shutil.rmtree(d)

    for f in files_to_remove:
        if os.path.exists(f):
            print(f"Removing {f}")
            os.remove(f)

    # Clean __pycache__ in subfolders
    for root, dirs, files in os.walk('.'):
        for d in dirs:
            if d == '__pycache__':
                path = os.path.join(root, d)
                print(f"Removing {path}")
                shutil.rmtree(path)

    print("Clean complete!")


def list_exclusions():
    """List packages that will be excluded"""
    installed = get_installed_packages()
    exclusions = get_exclusions()

    print(f"\nInstalled packages ({len(installed)}):")
    print("-" * 40)
    for pkg in sorted(installed):
        status = "KEEP" if pkg not in exclusions else "EXCLUDE"
        print(f"  [{status:7}] {pkg}")

    print(f"\nTotal to exclude: {len(exclusions)} packages")
    print()


def build_exe():
    """Build the executable"""
    print("=" * 50)
    print("AutomaPrint Server - Build Script")
    print("=" * 50)
    print()

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("ERROR: PyInstaller not installed!")
        print("Run: pip install pyinstaller")
        sys.exit(1)

    # Clean previous build
    print("\n[1/4] Cleaning previous build...")
    clean_build()

    # Get exclusions
    print("\n[2/4] Analyzing packages...")
    exclusions = get_exclusions()
    print(f"       Excluding {len(exclusions)} unnecessary packages")

    # Build command
    print("\n[3/4] Building executable...")

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=AutomaPrint',
        '--onefile',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--noupx',
        '--icon=assets/icon.ico',                         # App icon
        '--add-data=assets/icon.ico;.',                   # Include icon for runtime
        '--add-data=assets/blank.pdf;.',                  # Include test PDF
        '--add-binary=assets/SumatraPDF-3.5.2-32.exe;.',  # Include SumatraPDF
    ]

    # Add exclusions
    for pkg in exclusions:
        cmd.append(f'--exclude-module={pkg}')

    # Add hidden imports (required modules)
    hidden_imports = [
        'flask', 'werkzeug', 'werkzeug.serving',
        'jinja2', 'markupsafe', 'itsdangerous', 'click', 'blinker',
        'win32print', 'win32api', 'win32gui', 'win32con',
        # pystray requires all these for Windows
        'pystray', 'pystray._base', 'pystray._win32', 'pystray._util',
        'six',  # pystray dependency
        # PIL/Pillow
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL._imaging',
        'psutil',
    ]
    for module in hidden_imports:
        cmd.append(f'--hidden-import={module}')

    # Entry point
    cmd.append('main.py')

    print(f"       Running PyInstaller...")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("\nERROR: Build failed!")
        sys.exit(1)

    # Check output
    exe_path = os.path.join('dist', 'AutomaPrint.exe')
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n[4/4] Build successful!")
        print(f"       Output: {exe_path}")
        print(f"       Size: {size_mb:.1f} MB")
    else:
        print("\nERROR: Executable not found!")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("BUILD COMPLETE!")
    print("=" * 50)
    print(f"\nExecutable: {os.path.abspath(exe_path)}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Data folder: %USERPROFILE%\\AutomaPrint\\")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == '--clean':
            clean_build()
        elif arg == '--list':
            list_exclusions()
        elif arg in ['--help', '-h']:
            print(__doc__)
        else:
            print(f"Unknown argument: {arg}")
            print(__doc__)
    else:
        build_exe()


if __name__ == "__main__":
    main()
