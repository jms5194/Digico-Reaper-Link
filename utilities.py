import configparser
import ipaddress
import os.path
import socket
import threading
import time
from typing import Callable

import appdirs
import psutil
import wx
from configupdater import ConfigUpdater
from pubsub import pub
from pythonosc import dispatcher, osc_server, udp_client
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

import configure_reaper
from app_settings import settings
from consoles import Console, DiGiCo, StuderVista
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
        if ipaddress.IPv4Address(console_ip) in ipaddress.IPv4Network(interface_ip_string, False):
            return i[0]
        else:
            pass


class ManagedThread(threading.Thread):
    # Building threads that we can more easily control
    def __init__(self, target, name=None, daemon=True):
        super().__init__(target=target, name=name, daemon=daemon)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class ReaperDigicoOSCBridge:
    _console: Console

    def __init__(self):
        logger.info("Initializing ReaperDigicoOSCBridge")
        self.repeater_osc_thread = None
        self.reaper_osc_thread = None
        self.console_connection_thread = None
        self.digico_dispatcher = None
        self.reaper_dispatcher = None
        self.repeater_dispatcher = None
        self.console_client = None
        self.reaper_client = None
        self.repeater_client = None
        self.digico_osc_server = None
        self.reaper_osc_server = None
        self.repeater_osc_server = None
        self.requested_macro_num = None
        self.requested_snapshot_number = None
        self.snapshot_ignore_flag = False
        self.name_to_match = ""
        self.is_playing = False
        self.is_recording = False
        self.ini_prefs = ""
        self.config_dir = ""
        self.lock = threading.Lock()
        self.where_to_put_user_data()
        self.check_configuration()
        self.console_name_event = threading.Event()
        self.reaper_send_lock = threading.Lock()
        self._console = Console()
        pub.subscribe(self.handle_cue_load, "handle_cue_load")
        pub.subscribe(self.place_marker_with_name, "place_marker_with_name")
        pub.subscribe(self.incoming_transport_action, "incoming_transport_action")

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
        # Checking if a .ini config already exists for this app, if not call
        # build_initial_ini
        try:
            if os.path.isfile(self.ini_prefs):
                self.set_vars_from_pref(self.ini_prefs)
            else:
                self.build_initial_ini(self.ini_prefs)
        except Exception as e:
            logger.error(f"Failed to check/initialize config file: {e}")
            self.build_initial_ini(self.ini_prefs)

    @staticmethod
    def set_vars_from_pref(config_file_loc):
        # Bring in the vars to fill out settings from the preferences file
        logger.info("Setting variables from preferences file")
        config = configparser.ConfigParser()
        config.read(config_file_loc)
        settings.update_from_config(config)

    def build_initial_ini(self, location_of_ini):
        # Builds a .ini configuration file with default settings.
        # What should our defaults be? All zeros? Something technically valid?
        logger.info("Building initial .ini config file")
        config = configparser.ConfigParser()
        config["main"] = {}
        config["main"]["default_ip"] = "10.10.13.10"
        config["main"]["repeater_ip"] = "10.10.13.11"
        config["main"]["default_digico_send_port"] = "8001"
        config["main"]["default_digico_receive_port"] = "8000"
        config["main"]["default_reaper_send_port"] = "49102"
        config["main"]["default_reaper_receive_port"] = "49101"
        config["main"]["default_repeater_send_port"] = "9999"
        config["main"]["default_repeater_receive_port"] = "9998"
        config["main"]["forwarder_enabled"] = "False"
        config["main"]["window_pos_x"] = "400"
        config["main"]["window_pos_y"] = "222"
        config["main"]["window_size_x"] = "221"
        config["main"]["window_size_y"] = "310"
        config["main"]["name_only_match"] = "False"
        config["main"]["console_type"] = DiGiCo.type

        with open(location_of_ini, "w") as configfile:
            config.write(configfile)
        timeout = 2
        start_time = time.time()
        # Check to make sure the config file has been created before moving on.
        while not os.path.isfile(location_of_ini):
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Failed to create config file at {location_of_ini}")
            time.sleep(0.1)
        self.set_vars_from_pref(self.ini_prefs)

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
    ):
        # Given new values from the GUI, update the config file and restart the OSC Server
        logger.info("Updating configuration file")
        updater = ConfigUpdater()
        updater.read(self.ini_prefs)
        try:
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
        except Exception as e:
            logger.error(f"Failed to update config file: {e}")
        updater.update_file()
        self.set_vars_from_pref(self.ini_prefs)
        self.close_servers()
        self.restart_servers()

    @staticmethod
    def CheckReaperPrefs(rpr_rcv, rpr_send):
        if configure_reaper.osc_interface_exists(configure_reaper.get_resource_path(True), rpr_rcv, rpr_send):
            logger.info("Reaper OSC interface config already exists")
            return True
        else:
            logger.info("Reaper OSC interface config does not exist")
            return False

    @staticmethod
    def AddReaperPrefs(rpr_rcv, rpr_send):
        configure_reaper.add_OSC_interface(configure_reaper.get_resource_path(True), rpr_rcv, rpr_send)

    def update_pos_in_config(self, win_pos_tuple):
        # Receives the position of the window from the UI and stores it in the preferences file
        logger.info("Updating window position in config file")
        updater = ConfigUpdater()
        updater.read(self.ini_prefs)
        try:
            updater["main"]["window_pos_x"] = str(win_pos_tuple[0])
            updater["main"]["window_pos_y"] = str(win_pos_tuple[1])
        except Exception as e:
            logger.error(f"Failed to update window position in config file: {e}")
        updater.update_file()

    def update_size_in_config(self, win_size_tuple):
        logger.info("Updating window size in config file")
        updater = ConfigUpdater()
        updater.read(self.ini_prefs)
        try:
            updater["main"]["window_size_x"] = str(win_size_tuple[0])
            updater["main"]["window_size_y"] = str(win_size_tuple[1])
        except Exception as e:
            logger.error(f"Failed to update window size in config file: {e}")
        updater.update_file()

    def ValidateReaperPrefs(self):
        # If the Reaper .ini file does not contain an entry for Digico-Reaper Link, add one.
        try:
            if not self.CheckReaperPrefs(settings.reaper_receive_port, settings.reaper_port):
                self.AddReaperPrefs(settings.reaper_receive_port, settings.reaper_port)
                pub.sendMessage("reset_reaper", resetreaper=True)
            return True
        except RuntimeError as e:
            # If reaper is not running, send an error to the UI
            logger.debug(f"Reaper not running: {e}")
            pub.sendMessage('reaper_error', reapererror=e)
            return False

    def start_managed_thread(self, attr_name: str, target: Callable) -> None:
        # Start a ManagedThread that can be signaled to stop
        thread = ManagedThread(target=target, daemon=True)
        setattr(self, attr_name, thread)
        thread.start()

    def start_threads(self):
        # Start all OSC server threads
        logger.info("Starting OSC Server threads")
        self.start_managed_thread("reaper_osc_thread", self.build_reaper_osc_servers)
        self.start_managed_thread("heartbeat_thread", self.heartbeat_loop)
        if settings.console_type == DiGiCo.type:
            self.console = DiGiCo()
            self.console.start_managed_threads(self.start_managed_thread)
        elif settings.console_type == StuderVista.type:
            self.console = StuderVista()
            self.console.start_managed_threads(self.start_managed_thread)

    @property
    def console(self) -> Console:
        return self._console

    @console.setter
    def console(self, value: Console) -> None:
        self._console = value
        pub.sendMessage("console_type_updated", console=value)


    def build_reaper_osc_servers(self):
        # Connect to Reaper via OSC
        logger.info("Starting Reaper OSC server")
        self.reaper_client = udp_client.SimpleUDPClient(settings.reaper_ip, settings.reaper_port)
        self.reaper_dispatcher = dispatcher.Dispatcher()
        self.receive_reaper_OSC()
        try:
            self.reaper_osc_server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", settings.reaper_receive_port),
                                                                      self.reaper_dispatcher)
            logger.info("Reaper OSC server started")
            self.reaper_osc_server.serve_forever()
        except Exception as e:
            logger.error(f"Reaper OSC server startup error: {e}")

    # Reaper Functions:

    def place_marker_at_current(self):
        # Uses a reaper OSC action to place a marker at the current timeline spot
        logger.info("Placing marker at current time")
        with self.reaper_send_lock:
            self.reaper_client.send_message("/action", 40157)

    def update_last_marker_name(self, name):
        with self.reaper_send_lock:
            self.reaper_client.send_message("/lastmarker/name", name)

    def place_marker_with_name(self, marker_name):
        with self.reaper_send_lock:
            self.reaper_client.send_message("/action", 40157)
            self.reaper_client.send_message("/lastmarker/name", marker_name)

    def get_marker_id_by_name(self, name):
        # Asks for current marker information based upon number of markers.
        if self.is_playing is False:
            self.name_to_match = name
        if settings.name_only_match == "True":
            self.name_to_match = self.name_to_match.split(" ")
            self.name_to_match = self.name_to_match[1:]
            self.name_to_match = " ".join(self.name_to_match)
        with self.reaper_send_lock:
            self.reaper_client.send_message("/device/marker/count", 0)
            # Is there a better way to handle this in OSC only? Max of 512 markers.
            self.reaper_client.send_message("/device/marker/count", 512)

    def marker_matcher(self, OSCAddress, test_name):
        # Matches a marker composite name with its Reaper ID
        address_split = OSCAddress.split("/")
        marker_id = address_split[2]
        if settings.name_only_match == "True":
            test_name = test_name.split(" ")
            test_name = test_name[1:]
            test_name = " ".join(test_name)
        if test_name == self.name_to_match:
            self.goto_marker_by_id(marker_id)

    def goto_marker_by_id(self, marker_id):
        with self.reaper_send_lock:
            self.reaper_client.send_message("/marker", int(marker_id))

    def current_transport_state(self, OSCAddress, val):
        # Watches what the Reaper playhead is doing.
        playing = None
        recording = None
        if OSCAddress == "/play":
            if val == 0:
                playing = False
            elif val == 1:
                playing = True
        elif OSCAddress == "/record":
            if val == 0:
                recording = False
            elif val == 1:
                recording = True
        if playing is True:
            self.is_playing = True
            logger.info("Reaper is playing")
        elif playing is False:
            self.is_playing = False
            logger.info("Reaper is not playing")
        if recording is True:
            self.is_recording = True
            logger.info("Reaper is recording")
        elif recording is False:
            self.is_recording = False
            logger.info("Reaper is not recording")

    def incoming_transport_action(self, transport_action):
        if transport_action == "play":
            self.reaper_play()
        elif transport_action == "stop":
            self.reaper_stop()
        elif transport_action == "rec":
            self.reaper_rec()

    def reaper_play(self):
        with self.reaper_send_lock:
            self.reaper_client.send_message("/action", 1007)

    def reaper_stop(self):
        with self.reaper_send_lock:
            self.reaper_client.send_message("/action", 1016)

    def reaper_rec(self):
        # Sends action to skip to end of project and then record, to prevent overwrites
        settings.marker_mode = "Recording"
        pub.sendMessage("mode_select_osc", selected_mode="Recording")
        with self.reaper_send_lock:
            self.reaper_client.send_message("/action", 40043)
            self.reaper_client.send_message("/action", 1013)

    def receive_reaper_OSC(self):
        # Receives and distributes OSC from Reaper, based on matching OSC values
        self.reaper_dispatcher.map("/marker/*/name", self.marker_matcher)
        self.reaper_dispatcher.map("/play", self.current_transport_state)
        self.reaper_dispatcher.map("/record", self.current_transport_state)

    # Console Functions:

    def console_type_and_connected_check(self):
        if isinstance(self.console, Console):
            heartbeat=self.console.heartbeat()
            if isinstance(heartbeat,str):
                pub.sendMessage("console_connected", consolename=heartbeat)
            elif heartbeat:
                pub.sendMessage("console_connected", consolename="Connected")


    def heartbeat_loop(self):
        # Periodically requests the console name every 3 seconds
        # to verify connection status and update the UI
        while not self.console_name_event.is_set():
            try:
                self.console_type_and_connected_check()
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
            time.sleep(3)

    def handle_cue_load(self, cue: str) -> None:
        if settings.marker_mode == "Recording" and self.is_recording is True:
            self.place_marker_at_current()
            self.update_last_marker_name(cue)
        elif settings.marker_mode == "PlaybackTrack" and self.is_playing is False:
            self.get_marker_id_by_name(cue)

    def process_transport_macros(self, transport):
        try:
            if transport == "play":
                self.reaper_play()
            elif transport == "stop":
                self.reaper_stop()
            elif transport == "rec":
                self.reaper_rec()
        except Exception as e:
            logger.error(f"Could not process transport macro: {e}")


    def stop_all_threads(self):
        logger.info("Stopping all threads")
        for attr in [
            "console_connection_thread",
            "reaper_osc_thread",
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

        try:
            if self.digico_osc_server:
                self.digico_osc_server.shutdown()
                self.digico_osc_server.server_close()
            if self.reaper_osc_server:
                self.reaper_osc_server.shutdown()
                self.reaper_osc_server.server_close()
            if self.repeater_osc_server:
                self.repeater_osc_server.shutdown()
                self.repeater_osc_server.server_close()
        except Exception as e:
            logger.error(f"Error shutting down server: {e}")

        self.stop_all_threads()

        logger.info("All servers closed and threads joined.")
        return True

    def restart_servers(self):
        # Restart the OSC server threads.
        logger.info("Restarting OSC Server threads")
        self.console_name_event = threading.Event()
        self.start_threads()
