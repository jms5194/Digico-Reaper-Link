import threading
import os.path
import configparser
from configupdater import ConfigUpdater
import appdirs
from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server
import socket
import psutil
import settings


class ReaperDigicoOSCBridge:

    def __init__(self):
        self.repeater_osc_thread = None
        self.reaper_osc_thread = None
        self.digico_osc_thread = None
        self.digico_dispatcher = None
        self.reaper_dispatcher = None
        self.repeater_dispatcher = None
        self.console_client = None
        self.reaper_client = None
        self.repeater_client = None
        self.digico_osc_server = None
        self.reaper_osc_server = None
        self.repeater_osc_server = None
        self.name_to_match = ""
        self.is_playing = False
        self.is_recording = False
        self.ini_prefs = ""
        self.config_dir = ""
        self.lock = threading.Lock()
        self.where_to_put_user_data()
        self.check_configuration()
        self.start_threads()

    def where_to_put_user_data(self):
        appname = "Digico-Reaper Link"
        appauthor = "Justin Stasiw"
        self.config_dir = appdirs.user_config_dir(appname, appauthor)
        if os.path.isdir(self.config_dir):
            pass
        else:
            os.makedirs(self.config_dir)
        self.ini_prefs = self.config_dir + "/settings.cfg"
    def check_configuration(self):
        # Checking if a .cfg config already exists for this app, if not call
        # build_initial_ini
        try:
            if os.path.isfile(self.ini_prefs):
                self.set_vars_from_pref(self.ini_prefs)
            else:
                self.build_initial_ini(self.ini_prefs)
        except Exception as e:
            print(e)
            self.build_initial_ini(self.ini_prefs)

    def set_vars_from_pref(self, config_file_loc):
        config = configparser.ConfigParser()
        config.read(config_file_loc)
        settings.console_ip = config["main"]["default_ip"]
        settings.local_ip = config["main"]["local_ip"]
        settings.repeater_ip = config["main"]["repeater_ip"]
        settings.console_port = int(config["main"]["default_digico_send_port"])
        settings.receive_port = int(config["main"]["default_digico_receive_port"])
        settings.reaper_port = int(config["main"]["default_reaper_send_port"])
        settings.repeater_port = int(config["main"]["default_repeater_send_port"])
        settings.repeater_receive_port = int(config["main"]["default_repeater_receive_port"])
        settings.reaper_receive_port = int(config["main"]["default_reaper_receive_port"])
        settings.forwarder_enabled = config["main"]["forwarder_enabled"]
        settings.window_loc = (int(config["main"]["window_pos_x"]), int(config["main"]["window_pos_y"]))

    def build_initial_ini(self, location_of_ini):
        # Builds a .ini configuration file with default settings.
        config = configparser.ConfigParser()
        config["main"] = {}
        config["main"]["default_ip"] = "10.10.13.10"
        config["main"]["local_ip"] = "10.10.13.100"
        config["main"]["repeater_ip"] = "10.10.13.11"
        config["main"]["default_digico_send_port"] = "8001"
        config["main"]["default_digico_receive_port"] = "8000"
        config["main"]["default_reaper_send_port"] = "9999"
        config["main"]["default_reaper_receive_port"] = "9998"
        config["main"]["default_repeater_send_port"] = "9999"
        config["main"]["default_repeater_receive_port"] = "9998"
        config["main"]["forwarder_enabled"] = "False"
        config["main"]["window_pos_x"] = "400"
        config["main"]["window_pos_y"] = "222"

        with open(location_of_ini, "w") as configfile:
            config.write(configfile)
        self.set_vars_from_pref(config)

    def update_configuration(self, con_ip, local_ip, rptr_ip, con_send, con_rcv, fwd_enable, rpr_send, rpr_rcv,
                             rptr_snd, rptr_rcv):
        # Given new values from the GUI, update the config file and restart the OSC Server
        updater = ConfigUpdater()
        updater.read(self.ini_prefs)
        try:
            updater["main"]["default_ip"] = con_ip
            updater["main"]["local_ip"] = local_ip
            updater["main"]["repeater_ip"] = rptr_ip
            updater["main"]["default_digico_send_port"] = str(con_send)
            updater["main"]["default_digico_receive_port"] = str(con_rcv)
            updater["main"]["default_reaper_send_port"] = str(rpr_send)
            updater["main"]["default_reaper_receive_port"] = str(rpr_rcv)
            updater["main"]["default_repeater_send_port"] = str(rptr_snd)
            updater["main"]["default_repeater_receive_port"] = str(rptr_rcv)
            updater["main"]["forwarder_enabled"] = str(fwd_enable)
        except Exception as e:
            print(e)
        updater.update_file()
        self.set_vars_from_pref(self.ini_prefs)
        self.close_servers()
        self.restart_servers()

    def update_pos_in_config(self, win_pos_tuple):
        updater = ConfigUpdater()
        updater.read(self.ini_prefs)
        try:
            updater["main"]["window_pos_x"] = str(win_pos_tuple[0])
            updater["main"]["window_pos_y"] = str(win_pos_tuple[1])
        except Exception as e:
            print(e)
        updater.update_file()

    def start_threads(self):
        # Builds the threads for the OSC servers to run in, non-blocking.
        self.digico_osc_thread = threading.Thread(target=self.build_digico_osc_servers, daemon=False)
        self.reaper_osc_thread = threading.Thread(target=self.build_reaper_osc_servers, daemon=False)
        self.repeater_osc_thread = threading.Thread(target=self.build_repeater_osc_servers, daemon=False)
        self.digico_osc_thread.start()
        self.reaper_osc_thread.start()
        if settings.forwarder_enabled == "True":
            self.repeater_osc_thread.start()

    def build_digico_osc_servers(self):
        # Connect to the Digico console
        self.console_client = udp_client.SimpleUDPClient(settings.console_ip, settings.console_port)
        self.digico_dispatcher = dispatcher.Dispatcher()
        self.receive_console_OSC()
        try:
            self.digico_osc_server = osc_server.ThreadingOSCUDPServer((settings.local_ip, settings.receive_port),
                                                                      self.digico_dispatcher)
            print("Digico OSC server started.")
            self.digico_osc_server.serve_forever()
        except Exception as e:
            print("Unable to establish connection to Digico")

    def build_reaper_osc_servers(self):
        # Connect to Reaper via OSC
        self.reaper_client = udp_client.SimpleUDPClient(settings.reaper_ip, settings.reaper_port)
        self.reaper_dispatcher = dispatcher.Dispatcher()
        self.receive_reaper_OSC()
        try:
            self.reaper_osc_server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", settings.reaper_receive_port),
                                                                      self.reaper_dispatcher)
            print("Reaper OSC server started")
            self.reaper_osc_server.serve_forever()
        except Exception as e:
            print("Unable to establish connection to Reaper")

    def build_repeater_osc_servers(self):
        # Connect to Repeater via OSC
        self.repeater_client = udp_client.SimpleUDPClient(settings.repeater_ip, settings.repeater_port)
        self.repeater_dispatcher = dispatcher.Dispatcher()
        self.receive_repeater_OSC()
        try:
            self.repeater_osc_server = osc_server.ThreadingOSCUDPServer(
                (settings.local_ip, settings.repeater_receive_port),
                self.repeater_dispatcher)
            print("Repeater OSC server started")
            self.repeater_osc_server.serve_forever()
        except Exception as e:
            print("Unable to establish connection to repeater")

    def find_local_ip_in_subnet(self):
        # Find our local interface in the same network as the console interface
        # Not yet implemented
        ipv4_interfaces = []
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == socket.AF_INET:
                    ipv4_interfaces.append((snic.address, snic.netmask))
        for i in ipv4_interfaces:
            test_ip_split = i[0].split(".")
            ip_split = settings.console_ip.split(".")
            if test_ip_split[0:3] == ip_split[0:3]:
                return i[0]
            # Need to figure out how to check subnet mask
            # Need to add ability to handle possibility of multiple matches

    # Reaper Functions:

    def place_marker_at_current(self):
        # Uses a reaper OSC action to place a marker at the current timeline spot
        self.reaper_client.send_message("/action", 40157)

    def update_last_marker_name(self, name):
        self.reaper_client.send_message("/lastmarker/name", name)

    def get_marker_id_by_name(self, name):
        # Asks for current marker information based upon number of markers.
        if self.is_playing is False:
            self.name_to_match = name
            self.reaper_client.send_message("/device/marker/count", 0)
            # Is there a better way to handle this in OSC only? Max of 512 markers.
            self.reaper_client.send_message("/device/marker/count", 512)

    def marker_matcher(self, OSCAddress, test_name):
        # Matches a marker composite name with its Reaper ID
        address_split = OSCAddress.split("/")
        marker_id = address_split[2]
        if test_name == self.name_to_match:
            self.goto_marker_by_id(marker_id)

    def goto_marker_by_id(self, marker_id):
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
            print("reaper is playing")
        elif playing is False:
            self.is_playing = False
            print("reaper is not playing")
        if recording is True:
            self.is_recording = True
            print("reaper is recording")
        elif recording is False:
            self.is_recording = False
            print("reaper is not recording")

    def reaper_play(self):
        self.reaper_client.send_message("/action", 1007)

    def reaper_stop(self):
        self.reaper_client.send_message("/action", 1016)

    def reaper_rec(self):
        # Sends action to skip to end of project and then record, to prevent overwrites
        self.reaper_client.send_message("/action", 40043)
        self.reaper_client.send_message("/action", 1013)

    def receive_reaper_OSC(self):
        # Receives and distributes OSC from Reaper, based on matching OSC values
        self.reaper_dispatcher.map("/marker/*/name", self.marker_matcher)
        self.reaper_dispatcher.map("/play", self.current_transport_state)
        self.reaper_dispatcher.map("/record", self.current_transport_state)

    # Digico Functions:

    def receive_console_OSC(self):
        # Receives and distributes OSC from Digico, based on matching OSC values
        self.digico_dispatcher.map("/Snapshots/Current_Snapshot", self.request_snapshot_info)
        self.digico_dispatcher.map("/Snapshots/name", self.snapshot_OSC_handler)
        self.digico_dispatcher.map("/Macros/Recall_Macro/*", self.request_macro_info)
        self.digico_dispatcher.map("/Macros/name", self.macro_name_handler)
        self.digico_dispatcher.set_default_handler(self.forward_OSC)

    def send_to_console(self, OSCAddress, *args):
        # Send an OSC message to the console
        self.console_client.send_message(OSCAddress, [*args])

    def request_snapshot_info(self, OSCAddress, CurrentSnapshotNumber):
        # Receives the OSC for the Current Snapshot Number and uses that to request the cue number/name
        if settings.forwarder_enabled == "True":
            try:
                self.repeater_client.send_message(OSCAddress, CurrentSnapshotNumber)
            except Exception as e:
                print(e)
        self.console_client.send_message("/Snapshots/name/?", CurrentSnapshotNumber)

    def request_macro_info(self, OSCAddress, pressed):
        # When a Macro is pressed, request the name of the macro
        macro_num = OSCAddress.split("/")[3]
        self.console_client.send_message("/Macros/name/?", int(macro_num))

    def macro_name_handler(self, OSCAddress, *args):
        # If macros match names, then send behavior to Reaper
        macro_name = args[1]
        macro_name = str(macro_name).lower()
        print(macro_name)
        if macro_name in ("reaper,rec", "reaper rec", "rec", "record", "reaper, record", "reaper record"):
            self.process_transport_macros("rec")
        elif macro_name in ("reaper,stop", "reaper stop", "stop"):
            self.process_transport_macros("stop")
        elif macro_name in ("reaper,play", "reaper play", "play"):
            self.process_transport_macros("play")
        elif macro_name in ("reaper,marker", "reaper marker", "marker"):
            self.process_marker_macro()

    def process_marker_macro(self):
        self.place_marker_at_current()
        self.update_last_marker_name("Marker Dropped")

    def snapshot_OSC_handler(self, OSCAddress, *args):
        # Processes the current cue number
        if settings.forwarder_enabled == "True":
            try:
                self.repeater_client.send_message(OSCAddress, [*args])
            except Exception as e:
                print(e)
        cue_name = args[3]
        cue_number = str(args[1] / 100)
        if settings.marker_mode == "Recording" and self.is_recording is True:
            self.place_marker_at_current()
            self.update_last_marker_name(cue_number + " " + cue_name)
        elif settings.marker_mode == "PlaybackTrack" and self.is_playing is False:
            self.get_marker_id_by_name(cue_number + " " + cue_name)

    def process_transport_macros(self, transport):
        try:
            if transport == "play":
                self.reaper_play()
            elif transport == "stop":
                self.reaper_stop()
            elif transport == "rec":
                self.reaper_rec()
        except Exception as e:
            print(e)

    # Repeater Functions:

    def receive_repeater_OSC(self):
        self.repeater_dispatcher.set_default_handler(self.send_to_console)

    def forward_OSC(self, OSCAddress, *args):
        if settings.forwarder_enabled == "True":
            try:
                self.repeater_client.send_message(OSCAddress, [*args])
            except Exception as e:
                print(e)

    def close_servers(self):
        try:
            self.digico_osc_server.shutdown()
            self.digico_osc_thread.join()
        except Exception as e:
            print(e)
        try:
            self.reaper_osc_server.shutdown()
            self.reaper_osc_thread.join()
        except Exception as e:
            print(e)
        try:
            self.repeater_osc_server.shutdown()
            self.repeater_osc_thread.join()
        except Exception as e:
            print(e)
        print("servers closed")
        return True

    def restart_servers(self):
        # Restart the OSC server threads.
        self.start_threads()
