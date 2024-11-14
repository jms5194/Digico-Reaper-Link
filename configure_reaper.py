from configparser import ConfigParser
from collections import OrderedDict
import os
import pathlib
import shutil
import psutil
import sys

# Many thanks to the programmers of Reapy and Reapy-boost for much of this code.

class CaseInsensitiveDict(OrderedDict):
    """OrderedDict with case-insensitive keys."""
    _dict: OrderedDict

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dict = OrderedDict(*args, **kwargs)
        for key, value in self._dict.items():
            self._dict[key.lower()] = value

    def __contains__(self, key):
        return key.lower() in self._dict

    def __getitem__(self, key):
        return self._dict[key.lower()]

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._dict[key.lower()] = value


class Config(ConfigParser):
    """Parser for REAPER .ini file."""

    def __init__(self, ini_file):
        super().__init__(
            strict=False, delimiters="=", dict_type=CaseInsensitiveDict
        )
        self.optionxform = str
        self.ini_file = ini_file
        if not os.path.exists(ini_file):
            pathlib.Path(ini_file).touch()
        self.read(self.ini_file, encoding='utf8')

    def write(self):
        # Backup config state before user has ever tried Reaper-Digico Link
        before_RD_file = self.ini_file + '.before-Reaper-Digico.bak'
        if not os.path.exists(before_RD_file):
            shutil.copy(self.ini_file, before_RD_file)
        # Backup current config
        shutil.copy(self.ini_file, self.ini_file + '.bak')
        # Write config
        with open(self.ini_file, "w", encoding='utf8') as f:
            super().write(f, False)


def add_OSC_interface(resource_path, rcv_port=8000, snd_port=9000):
    """Add a REAPER OSC Interface at a specified port.

    It is added by manually editing reaper.ini configuration file,
    which is loaded on startup. Thus, the added web interface will
    only be available after restarting REAPER.

    Nothing happens in case an osc interface already exists at
    ``port``.

    Parameters
    ----------
    resource_path : str
        Path to REAPER resource directory. Can be obtained with
        :func:`reapy_boost.config.resource_path.get_resource_path`.
    rcv_port : int
        OSC receive port. Default=``8000``.
    snd_port : int
        OSC device port. Default= ``9000``.
    """
    if osc_interface_exists(resource_path, rcv_port, snd_port):
        return
    config = Config(os.path.join(resource_path, "reaper.ini"))
    csurf_count = int(config["reaper"].get("csurf_cnt", "0"))
    csurf_count += 1
    config["reaper"]["csurf_cnt"] = str(csurf_count)
    key = "csurf_{}".format(csurf_count - 1)
    config["reaper"][key] = "OSC \"Reaper-Digico Link\" 3 {sndport} \"127.0.0.1\" {rcvport} 1024 10 \"\"".format(rcvport=rcv_port, sndport=snd_port)
    config.write()


def osc_interface_exists(resource_path, rcv_port, snd_port):
    """Return whether a REAPER OSC Interface exists at a given port.

    Parameters
    ----------
    resource_path : str
        Path to REAPER resource directory. Can be obtained with
        :func:`reapy_boost.config.resource_path.get_resource_path`.
    rcv_port : int
        OSC receive port. Default=``8000``.
    snd_port : int
        OSC device port. Default= ``9000``.

    Returns
    -------
    bool
        Whether a REAPER OSC Interface exists at ``port``.
    """
    config = Config(os.path.join(resource_path, "reaper.ini"))
    csurf_count = int(config["reaper"].get("csurf_cnt", "0"))
    for i in range(csurf_count):
        string = config["reaper"]["csurf_{}".format(i)]
        if string.startswith("OSC"):  # It's a web interface
            if string.split(" ")[4] == str(snd_port) and string.split(" ")[6] == str(rcv_port):  # It's the one
                return True
    return False


def get_resource_path(detect_portable_install):
    for i in get_candidate_directories(detect_portable_install):
        if os.path.exists(os.path.join(i, 'reaper.ini')):
            return i
    raise RuntimeError('Cannot find resource path')


def get_candidate_directories(detect_portable_install):
    if detect_portable_install:
        yield get_portable_resource_directory()
    if is_apple():
        yield os.path.expanduser('~/Library/Application Support/REAPER')
    elif is_windows():
        yield os.path.expandvars(r'$APPDATA\REAPER')
    else:
        yield os.path.expanduser('~/.config/REAPER')


def get_portable_resource_directory():
    process_path = get_reaper_process_path()
    if is_apple():
        return '/'.join(process_path.split('/')[:-4])
    return os.path.dirname(process_path)


def get_reaper_process_path():
    """Return path to currently running REAPER process.

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
                            )[0].lower() == 'reaper'
    ]
    if not processes:
        raise RuntimeError('No REAPER instance is currently running.')
    elif len(processes) > 1:
        raise RuntimeError(
            'More than one REAPER instance is currently running.'
        )
    return processes[0].info['exe']  # type:ignore


def is_apple() -> bool:
    """Return whether OS is macOS or OSX."""
    return sys.platform == "darwin"


def is_windows() -> bool:
    """Return whether OS is Windows."""
    return os.name == "nt"
