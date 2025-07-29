import os
import pathlib
import shutil
import psutil
import sys
import xml.etree.ElementTree as ET

def update_config_file(config_file):
    # Backup config state before this software modified it.
    before_file = config_file + ".before.bak"
    if not os.path.exists(before_file):
        shutil.copy(config_file, before_file)
    # Backup current config
    shutil.copy(config_file, config_file + ".bak")
    # Write config
    with open(config_file, "w", encoding="utf8") as f:
        f.write()

def add_OSC_interface(resource_path, rcv_port=8000, snd_port=9000):
    config = ET.parse(os.path.join(resource_path, "config"))
    root = config.getroot()
    for child in root:
        print(child.tag, child.attrib)

def get_resource_path(detect_portable_install):
    for i in get_candidate_directories(detect_portable_install):
        if os.path.exists(os.path.join(i, 'config')):
            return i
    raise RuntimeError('Cannot find resource path')

def get_candidate_directories(detect_portable_install):
    if detect_portable_install:
        yield get_portable_resource_directory()
    if is_apple():
        yield os.path.expanduser('~/Library/Preferences/ardour8')
    elif is_windows():
        yield os.path.expandvars(r'$LOCALAPPDATA\ardour8')
    else:
        yield os.path.expanduser('~/.config/ardour8')

def get_portable_resource_directory():
    process_path = get_ardour_process_path()
    if is_apple():
        return '/'.join(process_path.split('/')[:-4])
    return os.path.dirname(process_path)

def is_apple() -> bool:
    """Return whether OS is macOS or OSX."""
    return sys.platform == "darwin"

def is_windows() -> bool:
    """Return whether OS is Windows."""
    return os.name == "nt"

def get_ardour_process_path():
    """Return path to currently running Ardour8 process.

    Returns
    -------
    str
        Path to executable file.

    Raises
    ------
    RuntimeError
        When zero or more than one REAPER instances are currently
        running.
    """
    processes = [
        p for p in psutil.process_iter(['name', 'exe'])
        if os.path.splitext(p.info['name']  # type:ignore
                            )[0].lower() == 'ardour8'
    ]
    if not processes:
        raise RuntimeError('No Ardour instance is currently running.')
    elif len(processes) > 1:
        raise RuntimeError(
            'More than one Ardour instance is currently running.'
        )
    return processes[0].info['exe']  # type:ignore