import os
import shutil
import xml.etree.ElementTree
from logger_config import logger
import psutil
import sys
import xml.etree.ElementTree as ET

def backup_config_file(config_file_path):
    # Backup config state before this software modified it.
    config_file_path = config_file_path + "/" + "config"
    before_file = config_file_path + ".before.bak"
    if not os.path.exists(before_file):
        shutil.copy(config_file_path, before_file)
    # Backup current config
    shutil.copy(config_file_path, config_file_path + ".bak")

def add_OSC_interface(resource_path, rcv_port=8000, snd_port=9000):
    # Parse the XML configuration document
    config = ET.parse(os.path.join(resource_path, "config"))
    root = config.getroot()
    osc_config = root.find("./ControlProtocols/Protocol[@name='Open Sound Control (OSC)']")
    osc_config.attrib["feedback"] = "16"
    osc_config.attrib["debugmode"] = "0"
    osc_config.attrib["address-only"] = "1"
    osc_config.attrib["remote-port"] = "3820"
    osc_config.attrib["banksize"] = "0"
    osc_config.attrib["striptypes"] = "31"
    osc_config.attrib["gainmode"] = "0"
    osc_config.attrib["send-page-size"] = "0"
    osc_config.attrib["active"] = "1"
    backup_config_file(resource_path)
    config.write("config")

def osc_interface_exists(resource_path, rcv_port, snd_port):
    config = ET.parse(os.path.join(resource_path, "config"))
    root = config.getroot()
    osc_config = root.find("./ControlProtocols/Protocol[@name='Open Sound Control (OSC)']")
    assert isinstance(osc_config, xml.etree.ElementTree.Element)
    try:
        if (osc_config.attrib["feedback"] == "16"
            and osc_config.attrib["debugmode"] == "0"
            and osc_config.attrib["address-only"] == "1"
            and osc_config.attrib["remote-port"] == "3820"
            and osc_config.attrib["banksize"] == "0"
            and osc_config.attrib["striptypes"] == "31"
            and osc_config.attrib["gainmode"] == "0"
            and osc_config.attrib["send-page-size"] == "0"
            and osc_config.attrib["active"] == "1"
            ):
            return True
        else:
            add_OSC_interface(resource_path, rcv_port, snd_port)
    except KeyError:
        logger.error("Ardour config is missing keys")

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
    # Return path to currently running Ardour8 process.
    processes = [
        p for p in psutil.process_iter(['name', 'exe'])
        if os.path.splitext(p.info['name']  # type:ignore
                            )[0].lower() in ['ardour8', "ardourgui"]
    ]
    if not processes:
        raise RuntimeError('No Ardour instance is currently running.')
    elif len(processes) > 1:
        raise RuntimeError(
            'More than one Ardour instance is currently running.'
        )
    return processes[0].info['exe']  # type:ignore