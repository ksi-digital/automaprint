# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/icon.ico', '.'), ('assets/blank.pdf', '.')],
    hiddenimports=['flask', 'werkzeug', 'werkzeug.serving', 'jinja2', 'markupsafe', 'itsdangerous', 'click', 'blinker', 'win32print', 'win32api', 'win32gui', 'win32con', 'pystray', 'pystray._base', 'pystray._win32', 'pystray._util', 'six', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL._imaging', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['certifi', 'charset_normalizer', 'et_xmlfile', 'idna', 'lxml', 'numpy', 'openpyxl', 'pandas', 'pip', 'python_dateutil', 'python_pptx', 'pytz', 'requests', 'tzdata', 'urllib3', 'xlsxwriter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AutomaPrint',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
)
