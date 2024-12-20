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
import time
from pubsub import pub
import configure_reaper
import ipaddress


class ReaperDigicoOSCBridge:

    def __init__(self):
        self.repeater_osc_thread = None
        self.reaper_osc_thread = None
        self.digico_osc_thread = None
        self.osc_cleanup_thread = None
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
        self.just_keep_cleaning = True
        self.ini_prefs = ""
        self.config_dir = ""
        self.lock = threading.Lock()
        self.where_to_put_user_data()
        self.check_configuration()

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
            print(e)
            self.build_initial_ini(self.ini_prefs)

    @staticmethod
    def set_vars_from_pref(config_file_loc):
        # Bring in the vars to fill out settings.py from the preferences file
        print("setting vars")
        config = configparser.ConfigParser()
        config.read(config_file_loc)
        settings.console_ip = config["main"]["default_ip"]
        settings.repeater_ip = config["main"]["repeater_ip"]
        settings.console_port = int(config["main"]["default_digico_send_port"])
        settings.receive_port = int(config["main"]["default_digico_receive_port"])
        settings.reaper_port = int(config["main"]["default_reaper_send_port"])
        settings.repeater_port = int(config["main"]["default_repeater_send_port"])
        settings.repeater_receive_port = int(config["main"]["default_repeater_receive_port"])
        settings.reaper_receive_port = int(config["main"]["default_reaper_receive_port"])
        settings.forwarder_enabled = config["main"]["forwarder_enabled"]
        settings.window_loc = int(config["main"]["window_pos_x"]), int(config["main"]["window_pos_y"])
        settings.window_size = int(config["main"]["window_size_x"]), int(config["main"]["window_size_y"])

    def build_initial_ini(self, location_of_ini):
        # Builds a .ini configuration file with default settings.
        # What should our defaults be? All zeros? Something technically valid?
        print("writing an initial config")
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

        with open(location_of_ini, "w") as configfile:
            config.write(configfile)
        time.sleep(1)
        self.set_vars_from_pref(self.ini_prefs)

    def update_configuration(self, con_ip, rptr_ip, con_send, con_rcv, fwd_enable, rpr_send, rpr_rcv,
                             rptr_snd, rptr_rcv):
        # Given new values from the GUI, update the config file and restart the OSC Server
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
        except Exception as e:
            print(e)
        updater.update_file()
        self.set_vars_from_pref(self.ini_prefs)
        self.close_servers()
        self.restart_servers()

    @staticmethod
    def CheckReaperPrefs(rpr_rcv, rpr_send):
        if configure_reaper.osc_interface_exists(configure_reaper.get_resource_path(True), rpr_rcv, rpr_send):
            return True

    @staticmethod
    def AddReaperPrefs(rpr_rcv, rpr_send):
        configure_reaper.add_OSC_interface(configure_reaper.get_resource_path(True), rpr_rcv, rpr_send)

    def update_pos_in_config(self, win_pos_tuple):
        # Receives the position of the window from the UI and stores it in the preferences file
        updater = ConfigUpdater()
        updater.read(self.ini_prefs)
        try:
            updater["main"]["window_pos_x"] = str(win_pos_tuple[0])
            updater["main"]["window_pos_y"] = str(win_pos_tuple[1])
        except Exception as e:
            print(e)
        updater.update_file()

    def update_size_in_config(self, win_size_tuple):
        updater = ConfigUpdater()
        updater.read(self.ini_prefs)
        try:
            updater["main"]["window_size_x"] = str(win_size_tuple[0])
            updater["main"]["window_size_y"] = str(win_size_tuple[1])
        except Exception as e:
            print(e)
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
            print(e)
            pub.sendMessage('reaper_error', reapererror=e)

    def start_threads(self):
        # Builds the threads for the OSC servers to run in, non-blocking.
        self.digico_osc_thread = threading.Thread(target=self.build_digico_osc_servers, daemon=False)
        self.reaper_osc_thread = threading.Thread(target=self.build_reaper_osc_servers, daemon=False)
        self.repeater_osc_thread = threading.Thread(target=self.build_repeater_osc_servers, daemon=False)
        self.osc_cleanup_thread = threading.Thread(target=self.osc_cleanup, daemon=False)
        self.digico_osc_thread.start()
        self.reaper_osc_thread.start()
        if settings.forwarder_enabled == "True":
            self.repeater_osc_thread.start()
        self.osc_cleanup_thread.start()

    def build_digico_osc_servers(self):
        # Connect to the Digico console
        self.console_client = udp_client.SimpleUDPClient(settings.console_ip, settings.console_port)
        self.digico_dispatcher = dispatcher.Dispatcher()
        self.receive_console_OSC()
        try:
            self.digico_osc_server = osc_server.ThreadingOSCUDPServer((self.find_local_ip_in_subnet
                                                                       (settings.console_ip),
                                                                       settings.receive_port),
                                                                      self.digico_dispatcher)
            print("Digico OSC server started.")
            self.console_type_and_connected_check()
            self.digico_osc_server.serve_forever()
        except Exception as e:
            print(e)
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
            print(e)
            print("Unable to establish connection to Reaper")

    def build_repeater_osc_servers(self):
        # Connect to Repeater via OSC
        self.repeater_client = udp_client.SimpleUDPClient(settings.repeater_ip, settings.repeater_port)
        self.repeater_dispatcher = dispatcher.Dispatcher()
        self.receive_repeater_OSC()
        try:
            self.repeater_osc_server = osc_server.ThreadingOSCUDPServer(
                (self.find_local_ip_in_subnet(settings.console_ip), settings.repeater_receive_port),
                self.repeater_dispatcher)
            print("Repeater OSC server started")
            self.repeater_osc_server.serve_forever()
        except Exception as e:
            print("Unable to establish connection to repeater")

    def osc_cleanup(self):
        # Dealing with a memory leak bug in Python's threading server. Threads don't close properly, and so leak memory.
        # This gets called occasionally to clean out dead threads.
        # As of 12/24, this is still required in high OSC loads. See issue #9
        try:
            while self.just_keep_cleaning is True:
                time.sleep(1)
                for thread in self.digico_osc_server._threads:
                    if not thread.is_alive():
                        self.digico_osc_server._threads.remove(thread)
                for thread in self.reaper_osc_server._threads:
                    if not thread.is_alive():
                        self.reaper_osc_server._threads.remove(thread)
                for thread in self.repeater_osc_server._threads:
                    if not thread.is_alive():
                        self.repeater_osc_server._threads.remove(thread)
        except:
            time.sleep(1)
            self.osc_cleanup()

    @staticmethod
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

    # Reaper Functions:

    def place_marker_at_current(self):
        # Uses a reaper OSC action to place a marker at the current timeline spot
        print("dropped Marker")
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
        settings.marker_mode = "Recording"
        pub.sendMessage("mode_select_osc", selected_mode="Recording")
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
        self.digico_dispatcher.map("/Console/Name", self.console_name_handler)
        self.digico_dispatcher.set_default_handler(self.forward_OSC)

    def send_to_console(self, OSCAddress, *args):
        # Send an OSC message to the console
        self.console_client.send_message(OSCAddress, [*args])

    def console_type_and_connected_check(self):
        # Asks the console for its name. This forms the heartbeat function of the UI
        self.console_client.send_message("/Console/Name/?", None)

    def console_name_handler(self, OSCAddress, ConsoleName):
        # Let's send the console name to the UI
        pub.sendMessage("console_name", consolename=ConsoleName)
        # Every 3 seconds, let's request the console name again
        time.sleep(3)
        self.console_type_and_connected_check()

    def request_snapshot_info(self, OSCAddress, CurrentSnapshotNumber):
        # Receives the OSC for the Current Snapshot Number and uses that to request the cue number/name
        if settings.forwarder_enabled == "True":
            try:
                self.repeater_client.send_message(OSCAddress, CurrentSnapshotNumber)
                print('requested snapshot info')
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
        elif macro_name in ("mode,rec", "mode,record", "mode,recording",
                            "mode rec", "mode record", "mode recording"):
            settings.marker_mode = "Recording"
            pub.sendMessage("mode_select_osc", selected_mode="Recording")
        elif macro_name in ("mode,track", "mode,tracking", "mode,PB Track",
                            "mode track", "mode tracking", "mode PB Track"):
            settings.marker_mode = "PlaybackTrack"
            pub.sendMessage("mode_select_osc", selected_mode="PlaybackTrack")
        elif macro_name in ("mode,no track", "mode,no tracking", "mode no track",
                            "mode no tracking"):
            settings.marker_mode = "PlaybackNoTrack"
            pub.sendMessage("mode_select_osc", selected_mode="PlaybackNoTrack")

    def process_marker_macro(self):
        self.place_marker_at_current()
        self.update_last_marker_name("Marker from Console")

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
        # Closing all of the OSC servers.
        try:
            self.digico_osc_server.server_close()
            self.digico_osc_server.shutdown()
            self.digico_osc_thread.join()
        except Exception as e:
            print(e)
        try:
            self.reaper_osc_server.server_close()
            self.reaper_osc_server.shutdown()
            self.reaper_osc_thread.join()
        except Exception as e:
            print(e)
        try:
            self.reaper_osc_server.server_close()
            self.repeater_osc_server.shutdown()
            self.repeater_osc_thread.join()
        except Exception as e:
            print(e)
        try:
            self.just_keep_cleaning = False
        except Exception as e:
            print(e)
        print("servers closed")
        return True

    def restart_servers(self):
        # Restart the OSC server threads.
        self.start_threads()
