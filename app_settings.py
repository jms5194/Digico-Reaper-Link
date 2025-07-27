import threading
from configparser import ConfigParser

from consoles import DiGiCo
from daws import Reaper

class ThreadSafeSettings:
    def __init__(self):
        self._lock = threading.Lock()
        self._settings = {
            'console_ip' : "10.10.10.1",
            'reaper_ip' : "127.0.0.1",
            'repeater_ip' : "10.10.10.10",
            'repeater_port' : 9999,
            'repeater_receive_port' : 9998,
            'reaper_port' : 49102,
            'reaper_receive_port' : 49101,
            'console_port' : 8001,
            'receive_port' : 8000,
            'forwarder_enabled' : False,
            'marker_mode' : "PlaybackTrack",
            'window_loc' : (400, 222),
            'window_size' : (221, 310),
            'name_only_match' : False,
            'console_type': DiGiCo.type,
            'daw_type' : Reaper.type
        }

    @property
    def console_ip(self) -> str:
        with self._lock:
            return self._settings["console_ip"]

    @console_ip.setter
    def console_ip(self, value):
        with self._lock:
            self._settings["console_ip"] = value

    @property
    def reaper_ip(self) -> str:
        with self._lock:
            return self._settings["reaper_ip"]

    @reaper_ip.setter
    def reaper_ip(self, value):
        with self._lock:
            self._settings["reaper_ip"] = value

    @property
    def repeater_ip(self) -> str:
        with self._lock:
            return self._settings["repeater_ip"]

    @repeater_ip.setter
    def repeater_ip(self, value):
        with self._lock:
            self._settings["repeater_ip"] = value

    @property
    def repeater_port(self) -> int:
        with self._lock:
            return self._settings["repeater_port"]

    @repeater_port.setter
    def repeater_port(self, value):
        with self._lock:
            port_num = int(value)
            if not 1 <= port_num <= 65535:
                raise ValueError("Invalid port number")
            self._settings["repeater_port"] = port_num

    @property
    def repeater_receive_port(self) -> int:
        with self._lock:
            return self._settings["repeater_receive_port"]

    @repeater_receive_port.setter
    def repeater_receive_port(self, value):
        with self._lock:
            port_num = int(value)
            if not 1 <= port_num <= 65535:
                raise ValueError("Invalid port number")
            self._settings["repeater_receive_port"] = port_num

    @property
    def reaper_port(self) -> int:
        with self._lock:
            return self._settings["reaper_port"]

    @reaper_port.setter
    def reaper_port(self, value):
        with self._lock:
            port_num = int(value)
            if not 1 <= port_num <= 65535:
                raise ValueError("Invalid port number")
            self._settings["reaper_port"] = port_num

    @property
    def reaper_receive_port(self) -> int:
        with self._lock:
            return self._settings["reaper_receive_port"]

    @reaper_receive_port.setter
    def reaper_receive_port(self, value):
        with self._lock:
            port_num = int(value)
            if not 1 <= port_num <= 65535:
                raise ValueError("Invalid port number")
            self._settings["reaper_receive_port"] = port_num

    @property
    def console_port(self) -> int:
        with self._lock:
            return self._settings["console_port"]

    @console_port.setter
    def console_port(self, value):
        with self._lock:
            port_num = int(value)
            if not 1 <= port_num <= 65535:
                raise ValueError("Invalid port number")
            self._settings["console_port"] = port_num

    @property
    def receive_port(self) -> int:
        with self._lock:
            return self._settings["receive_port"]

    @receive_port.setter
    def receive_port(self, value):
        with self._lock:
            port_num = int(value)
            if not 1 <= port_num <= 65535:
                raise ValueError("Invalid port number")
            self._settings["receive_port"] = port_num

    @property
    def forwarder_enabled(self) -> bool:
        with self._lock:
            return self._settings["forwarder_enabled"]

    @forwarder_enabled.setter
    def forwarder_enabled(self, value):
        with self._lock:
            self._settings["forwarder_enabled"] = value

    @property
    def marker_mode(self) -> str:
        with self._lock:
            return self._settings["marker_mode"]

    @marker_mode.setter
    def marker_mode(self, value):
        with self._lock:
            self._settings["marker_mode"] = value

    @property
    def window_loc(self):
        with self._lock:
            return self._settings["window_loc"]

    @window_loc.setter
    def window_loc(self, value):
        with self._lock:
            self._settings["window_loc"] = value

    @property
    def window_size(self):
        with self._lock:
            return self._settings["window_size"]

    @window_size.setter
    def window_size(self, value):
        with self._lock:
            self._settings["window_size"] = value

    @property
    def name_only_match(self) -> bool:
        with self._lock:
            return self._settings["name_only_match"]

    @name_only_match.setter
    def name_only_match(self, value):
        with self._lock:
            self._settings["name_only_match"] = value

    @property
    def console_type(self) -> str:
        with self._lock:
            return self._settings["console_type"]

    @console_type.setter
    def console_type(self, value):
        with self._lock:
            self._settings["console_type"] = value

    @property
    def daw_type(self) -> str:
        with self._lock:
            return self._settings["daw_type"]

    @daw_type.setter
    def daw_type(self, value):
        with self._lock:
            self._settings["daw_type"] = value

    def update_from_config(self, config: ConfigParser):
        # Update settings from a ConfigParser object
        with self._lock:
            string_properties = {
                "console_ip": "default_ip",
                "repeater_ip": "repeater_ip",
                "console_type": "console_type",
                # 'daw_type': 'daw_type',
            }
            for settings_name, config_name in string_properties.items():
                self._settings[settings_name] = config.get(
                    "main", config_name, fallback=self._settings[settings_name]
                )

            int_properties = {
                "console_port": "default_digico_send_port",
                "receive_port": "default_digico_receive_port",
                "reaper_port": "default_reaper_send_port",
                "repeater_port": "default_repeater_send_port",
                "repeater_receive_port": "default_repeater_receive_port",
                "reaper_receive_port": "default_reaper_receive_port",
            }
            for settings_name, config_name in int_properties.items():
                self._settings[settings_name] = config.getint(
                    "main", config_name, fallback=self._settings[settings_name]
                )

            boolean_properties = {
                "forwarder_enabled": "forwarder_enabled",
                "name_only_match": "name_only_match",
            }
            for settings_name, config_name in boolean_properties.items():
                self._settings[settings_name] = config.getboolean(
                    "main", config_name, fallback=self._settings[settings_name]
                )

            # Not implementing fallbacks for these since they've been around since the v3 config
            self._settings.update(
                {
                    "window_loc": (
                        int(config["main"]["window_pos_x"]),
                        int(config["main"]["window_pos_y"]),
                    ),
                    "window_size": (
                        int(config["main"]["window_size_x"]),
                        int(config["main"]["window_size_y"]),
                    ),
                }
            )


settings = ThreadSafeSettings()
