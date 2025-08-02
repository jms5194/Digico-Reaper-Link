import configparser
import ipaddress
import os.path
import socket
import threading
import time
from typing import Callable

import appdirs
import psutil
from configupdater import ConfigUpdater
from pubsub import pub

from app_settings import settings
from consoles import CONSOLES, Console
from daws import Ardour, Daw, ProTools, Reaper
from logger_config import logger


def find_local_ip_in_subnet(console_ip):
    # Find our local interface in the same network as the console interface
    ipv4_interfaces = []
    # Make a list of all the network interfaces on our machine
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == socket.AF_INET:
                ipv4_interfaces.append((snic.address, snic.netmask))
    # Iterate through network interfaces to see if any are in the same subnet as console
    for i in ipv4_interfaces:
        # Convert tuples to strings like 192.168.1.0/255.255.255.0 since thats what ipaddress expects
        interface_ip_string = i[0] + "/" + i[1]
        # If strict is off, then the user bits of the computer IP will be masked automatically
        # Need to add error handling here
        if ipaddress.IPv4Address(console_ip) in ipaddress.IPv4Network(
            interface_ip_string, False
        ):
            return i[0]
        else:
            pass
    return None


class ManagedThread(threading.Thread):
    # Building threads that we can more easily control
    def __init__(self, target, name=None, daemon=True):
        super().__init__(target=target, name=name, daemon=daemon)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class DawConsoleBridge:
    _console: Console

    def __init__(self):
        logger.info("Initializing ConsoleMarkerBridge")
        self.ini_prefs = ""
        self.config_dir = ""
        self.lock = threading.Lock()
        self.where_to_put_user_data()
        self.check_configuration()
        self.console_name_event = threading.Event()
        self._console = Console()
        self._daw = Daw()

    def where_to_put_user_data(self):
        # Find a home for our preferences file
        appname = "Digico-Reaper Link"
        appauthor = "Justin Stasiw"
        self.config_dir = appdirs.user_config_dir(appname, appauthor)
        if os.path.isdir(self.config_dir):
            pass
        else:
            os.makedirs(self.config_dir)
        self.ini_prefs = self.config_dir + "/settingsV3.ini"

    def check_configuration(self):
        # Load an existing configuration file, if one exists
        try:
            if os.path.isfile(self.ini_prefs):
                self.set_vars_from_pref(self.ini_prefs)
        except Exception as e:
            logger.error(f"Failed to check/initialize config file: {e}")

    @staticmethod
    def set_vars_from_pref(config_file_loc):
        # Bring in the vars to fill out settings from the preferences file
        logger.info("Setting variables from preferences file")
        config = configparser.ConfigParser()
        config.read(config_file_loc)
        settings.update_from_config(config)

    def update_configuration(
        self,
        con_ip,
        rptr_ip,
        con_send,
        con_rcv,
        fwd_enable,
        rpr_send,
        rpr_rcv,
        rptr_snd,
        rptr_rcv,
        name_only,
        console_type,
        daw_type,
        always_on_top: bool,
    ):
        # Given new values from the GUI, update the config file and restart the OSC Server
        logger.info("Updating configuration file")
        updater = ConfigUpdater()
        try:
            updater.read(self.ini_prefs)
        except FileNotFoundError:
            pass
        try:
            if not updater.has_section("main"):
                print("Adding main section")
                updater.add_section("main")
            updater["main"]["default_ip"] = con_ip
            updater["main"]["repeater_ip"] = rptr_ip
            updater["main"]["default_digico_send_port"] = str(con_send)
            updater["main"]["default_digico_receive_port"] = str(con_rcv)
            updater["main"]["default_reaper_send_port"] = str(rpr_send)
            updater["main"]["default_reaper_receive_port"] = str(rpr_rcv)
            updater["main"]["default_repeater_send_port"] = str(rptr_snd)
            updater["main"]["default_repeater_receive_port"] = str(rptr_rcv)
            updater["main"]["forwarder_enabled"] = str(fwd_enable)
            updater["main"]["name_only_match"] = str(name_only)
            updater["main"]["console_type"] = str(console_type)
            updater["main"]["daw_type"] = str(daw_type)
            updater["main"]["always_on_top"] = str(always_on_top)
        except Exception as e:
            logger.error(f"Failed to update config file: {e}")
        with open(self.ini_prefs, "w") as file:
            updater.write(file, validate=False)
        self.set_vars_from_pref(self.ini_prefs)
        self.close_servers()
        self.restart_servers()

    def update_pos_in_config(self, win_pos_tuple):
        # Receives the position of the window from the UI and stores it in the preferences file
        logger.info("Updating window position in config file")
        updater = ConfigUpdater()
        try:
            updater.read(self.ini_prefs)
        except FileNotFoundError:
            pass
        try:
            if not updater.has_section("main"):
                print("Adding main section")
                updater.add_section("main")
            updater.set("main", "window_pos_x", str(win_pos_tuple[0]))
            updater.set("main", "window_pos_y", str(win_pos_tuple[1]))
        except Exception as e:
            logger.error(f"Failed to update window position in config file: {e}")
        with open(self.ini_prefs, "w") as file:
            updater.write(file, validate=False)

    def update_size_in_config(self, win_size_tuple):
        logger.info("Updating window size in config file")
        updater = ConfigUpdater()
        try:
            updater.read(self.ini_prefs)
        except FileNotFoundError:
            pass
        try:
            if not updater.has_section("main"):
                print("Adding main section")
                updater.add_section("main")
            updater["main"]["window_size_x"] = str(win_size_tuple[0])
            updater["main"]["window_size_y"] = str(win_size_tuple[1])
        except Exception as e:
            logger.error(f"Failed to update window size in config file: {e}")
        with open(self.ini_prefs, "w") as file:
            updater.write(file, validate=False)

    def start_managed_thread(self, attr_name: str, target: Callable) -> None:
        # Start a ManagedThread that can be signaled to stop
        thread = ManagedThread(target=target, daemon=True)
        setattr(self, attr_name, thread)
        thread.start()

    def start_threads(self):
        # Start all OSC server threads
        logger.info("Starting threads")
        if settings.daw_type == Reaper.type:
            self.daw = Reaper()
        elif settings.daw_type == ProTools.type:
            self.daw = ProTools()
        elif settings.daw_type == Ardour.type:
            self.daw = Ardour()
        self.daw.start_managed_threads(self.start_managed_thread)
        self.start_managed_thread("heartbeat_thread", self.heartbeat_loop)
        if settings.console_type in CONSOLES:
            self.console: Console = CONSOLES[settings.console_type]()
            self.console.start_managed_threads(self.start_managed_thread)
        else:
            logger.error("Console is not supported!")

    @property
    def console(self) -> Console:
        return self._console

    @console.setter
    def console(self, value: Console) -> None:
        self._console = value
        pub.sendMessage("console_type_updated", console=value)

    @property
    def daw(self) -> Daw:
        return self._daw

    @daw.setter
    def daw(self, value: Daw) -> None:
        self._daw = value
        pub.sendMessage("daw_type_updated", daw=value)

    # Console Functions:

    def heartbeat_loop(self):
        # Periodically requests the console name every 3 seconds
        # to verify connection status and update the UI
        while not self.console_name_event.is_set():
            try:
                if isinstance(self.console, Console):
                    self.console.heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                pub.sendMessage("console_disconnected")
            time.sleep(3)

    def stop_all_threads(self):
        logger.info("Stopping all threads")
        for attr in [
            "console_connection_thread",
            "daw_connection_thread",
            "repeater_osc_thread",
            "heartbeat_thread",
        ]:
            thread = getattr(self, attr, None)
            if thread and isinstance(thread, ManagedThread):
                thread.stop()
                thread.join(timeout=1)

    def close_servers(self):
        logger.info("Closing OSC servers...")
        self.console_name_event.set()  # Signal heartbeat to exit
        pub.sendMessage("shutdown_servers")
        self.stop_all_threads()
        logger.info("All servers closed and threads joined.")
        return True

    def restart_servers(self):
        # Restart the OSC server threads.
        logger.info("Restarting server threads")
        self.console_name_event = threading.Event()
        self.start_threads()
