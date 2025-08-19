import inspect
import ipaddress
import os.path
import socket
import threading
import time
from typing import Callable, List

import appdirs
import psutil
from configupdater import ConfigUpdater
from pubsub import pub

import constants
import external_control
from app_settings import settings
from consoles import CONSOLES, Console
from constants import PyPubSubTopics
from daws import DAWS, Daw
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


class DawConsoleBridge:
    _console: Console
    _threads: List[threading.Thread] = list()

    def __init__(self):
        logger.info("Initializing ConsoleMarkerBridge")
        self.ini_path = ""
        self.config_dir = ""
        self.lock = threading.Lock()
        self._shutdown_server_event = threading.Event()
        self._server_restart_lock = threading.Lock()
        self._console = Console()
        self._daw = Daw()

        # The path to the legacy (v3) configuration file, we only read this
        self._legacy_ini_path = os.path.join(
            appdirs.user_config_dir(
                constants.APPLICATION_NAME_LEGACY, constants.APPLICATION_AUTHOR
            ),
            constants.CONFIG_FILENAME_LEGACY,
        )
        # The folder that the current configuration file is saved in
        ini_folder = appdirs.user_config_dir(
            constants.APPLICATION_NAME, constants.APPLICATION_AUTHOR
        )
        self._ini_path = os.path.join(
            ini_folder,
            constants.CONFIG_FILENAME,
        )
        if not os.path.isdir(ini_folder):
            os.makedirs(ini_folder)
        self.check_configuration()


    def check_configuration(self):
        "Check for a configuration file, and load settings from it"
        try:
            if os.path.isfile(self._ini_path):
                settings.update_from_config_file(self._ini_path)
            elif os.path.isfile(self._legacy_ini_path):
                logger.info("Loading settings from legacy (v3) ini")
                settings.update_from_config_file(self._legacy_ini_path)
        except Exception as e:
            logger.error(f"Failed to check/initialize config file: {e}")

    def update_configuration_file(
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
        always_on_top,
        external_control_osc_port,
        external_control_midi_port,
        mmc_control_enabled,
    ):
        "Update the configuration files with new values"
        # TODO: This can likely re-use the mapping that's used for reading the config file and loop through properties
        logger.info("Updating configuration file")
        updater = ConfigUpdater()
        try:
            updater.read(self._ini_path)
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
            updater["main"]["external_control_osc_port"] = str(
                external_control_osc_port
            )
            updater["main"]["external_control_midi_port"] = str(
                external_control_midi_port
            )
            updater["main"]["mmc_control_enabled"] = str(mmc_control_enabled)
        except Exception as e:
            logger.error(f"Failed to update config file: {e}")
        with open(self._ini_path, "w") as file:
            updater.write(file, validate=False)
        settings.update_from_config_file(self._ini_path)

    def update_pos_in_config(self, win_pos_tuple):
        # Receives the position of the window from the UI and stores it in the preferences file
        logger.info("Updating window position in config file")
        updater = ConfigUpdater()
        try:
            updater.read(self._ini_path)
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
        with open(self._ini_path, "w") as file:
            updater.write(file, validate=False)

    def start_managed_thread(self, attr_name: str, target: Callable) -> None:
        if "stop_event" in inspect.getargs(target.__code__).args:
            kwargs = {"stop_event": self._shutdown_server_event}
        else:
            kwargs = None
        thread = threading.Thread(target=target, kwargs=kwargs, daemon=True)
        self._threads.append(thread)
        thread.start()

    def start_threads(self):
        # Start all OSC server threads
        logger.info("Starting threads")
        if settings.daw_type in DAWS:
            self.daw: Daw = DAWS[settings.daw_type]()
            self.daw.start_managed_threads(self.start_managed_thread)
        self.start_managed_thread("heartbeat_thread", self.heartbeat_loop)
        if settings.console_type in CONSOLES:
            self.console: Console = CONSOLES[settings.console_type]()
            self.console.start_managed_threads(self.start_managed_thread)
        else:
            logger.error("Console is not supported!")
        self.start_managed_thread(
            "external_osc_control", external_control.external_osc_control
        )
        self.start_managed_thread(
            "external_midi_control", external_control.external_midi_control
        )

    @property
    def console(self) -> Console:
        return self._console

    @console.setter
    def console(self, value: Console) -> None:
        self._console = value
        pub.sendMessage(PyPubSubTopics.CONSOLE_DISCONNECTED)

    @property
    def daw(self) -> Daw:
        return self._daw

    @daw.setter
    def daw(self, value: Daw) -> None:
        self._daw = value
        pub.sendMessage(PyPubSubTopics.DAW_CONNECTION_STATUS, daw=value)

    # Console Functions:

    def heartbeat_loop(self):
        # Periodically requests the console name every 3 seconds
        # to verify connection status and update the UI
        while not self._shutdown_server_event.is_set():
            try:
                if isinstance(self.console, Console):
                    self.console.heartbeat()
            except Exception as e:
                logger.error(f"Console Heartbeat loop error: {e}")
                pub.sendMessage(PyPubSubTopics.CONSOLE_DISCONNECTED)
            time.sleep(3)

    def stop_all_threads(self):
        logger.info("Stopping all threads")
        for thread in self._threads:
            thread.join(timeout=constants.HIGHEST_THREAD_TIMEOUT * 2)
            # Only remove threads that managed to shut down
            if not thread.is_alive():
                self._threads.remove(thread)

    def close_servers(self):
        logger.info("Closing OSC servers...")
        self._shutdown_server_event.set()  # Signal heartbeat to exit
        pub.sendMessage(PyPubSubTopics.SHUTDOWN_SERVERS)
        self.stop_all_threads()
        logger.info("All servers closed and threads joined.")
        return True

    def restart_servers(self):
        logger.info("Restarting server threads")
        self._shutdown_server_event.clear()
        self.start_threads()

    def shutdown_and_restart_servers(self, as_thread: bool = True) -> None:
        if as_thread:
            threading.Thread(
                target=self.shutdown_and_restart_servers, args=(False,)
            ).start()
        else:
            with self._server_restart_lock:
                self.close_servers()
                self.restart_servers()

    def attempt_reconnect(self):
        logger.info("Manual reconnection requested")
        self.shutdown_and_restart_servers()


def get_resources_directory_path() -> str:
    py2app_resource_path = os.environ.get("RESOURCEPATH")
    if py2app_resource_path is not None:
        return py2app_resource_path
    return os.path.join(os.path.dirname(__file__), "resources")
