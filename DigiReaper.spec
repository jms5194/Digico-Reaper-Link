# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# parse command line arguments
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--mac_osx', action='store_true')
parser.add_argument('--win', action='store_true')
parser.add_argument('--debug', action='store_true')

args = parser.parse_args()

datas = [
    ('.env', '.'),
    ('resources/rprdigi.icns', './resources'),
    ('resources/rprdigi.ico', './resources'),
]



numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
ws_hiddenimports=['websockets', 'websockets.legacy']

a = Analysis(['main.py'],
    pathex=[],
    binaries=numpy_binaries,
    datas=datas + numpy_datas,
    hiddenimports=numpy_hiddenimports + ws_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
pyz = PYZ(a.pure)

if args.win:
    exe = EXE(
        pyz,
        a.scripts,
        name='Digico-Reaper Link',
        icon='resources/rprdigi.ico',
        debug=args.debug is not None and args.debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=args.debug is not None and args.debug,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Digico-Reaper Link'
    )
    app = BUNDLE(
        coll,
        name='Digico-Reaper Link.exe',
        icon= 'resources/rprdigi.ico',
        bundle_identifier=None
        )
elif args.mac_osx:
    exe = EXE(
        pyz,
        a.binaries,
        a.datas,
        a.scripts,
        name='Digico-Reaper Link',
        debug=args.debug is not None and args.debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=os.environ.get('APPLE_APP_DEVELOPER_ID', ''),
        entitlements_file='./entitlements.plist',
    )
    app = BUNDLE(
        exe,
        name='Digico-Reaper Link.app',
        icon='resources/rprdigi.icns',
        bundle_identifier='com.justinstasiw.digicoreaperlink',
        version='3.0.0',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
        }
    )
else:
    exe = EXE(
        pyz,
        a.binaries,
        a.datas,
        a.scripts,
        name='Digico-Reaper Link',
        icon='resources/rprdigi.ico',
        debug=args.debug is not None and args.debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
    )