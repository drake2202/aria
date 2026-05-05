# aria.spec
import sys

block_cipher = None

a = Analysis(
    ['aria/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('flash', 'flash'),
        ('maps', 'maps'),
    ],
    hiddenimports=[
        'PyQt5.QtWebEngineWidgets',
        'keyring.backends.macOS',
        'keyring.backends.SecretService',
        'keyring.backends.kwallet',
        'keyring.backends.chainer',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='aria',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='aria',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Aria.app',
        icon=None,
        bundle_identifier='com.drake2202.aria',
        info_plist={
            'CFBundleName': 'Aria',
            'CFBundleDisplayName': 'Aria Launcher',
            'CFBundleVersion': '1.1.0',
            'CFBundleShortVersionString': '1.1.0',
            'NSHighResolutionCapable': True,
        },
    )
