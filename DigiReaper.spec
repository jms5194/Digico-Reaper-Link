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
    ('resources/rprdigi.icns', './icons'),
    ('resources/rprdigi.ico', './icons'),
]

sources = [
    'src/settings.py',
    'src/utilities.py',
]


numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
ws_hiddenimports=['websockets', 'websockets.legacy']

a = Analysis(
    sources,
    pathex=[],
    binaries=numpy_binaries,
    datas=datas + numpy_datas,
    hiddenimports=numpy_hiddenimports + ws_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6'],
    noarchive=False,
)
pyz = PYZ(a.pure)

if args.win:
    exe = EXE(
        pyz,
        a.scripts,
        splash,
        name='Digico-Reaper Link',
        icon='icons/rprdigi.ico',
        debug=args.debug is not None and args.debug,
        exclude_binaries=True,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=args.debug is not None and args.debug,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        splash.binaries,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Digico-Reaper Link'
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
        icon='icons/rprdigi.icns',
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
        splash,
        splash.binaries,
        name='Digico-Reaper Link',
        icon='icons/rprdigi.ico',
        debug=args.debug is not None and args.debug,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
    )