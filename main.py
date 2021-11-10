# !/usr/bin/env python3
# -- coding: utf-8

"""Digico-Reaper Link"""

__author__ = "Justin Stasiw"
__version__ = "$Revision 1.0$"
__date__ = "$Date: 2021/11/10"

import sys
import time
import threading
import os.path
import plistlib
import appdirs
import PySimpleGUIQt as sg
from appdirs import *
from pythonosc import udp_client
from pythonosc import dispatcher
from pythonosc import osc_server


class ReaperDigicoOSCBridge:

    def __init__(self):
        self.console_ip = "10.10.13.10"
        self.reaper_ip = "127.0.0.1"
        self.local_ip = "127.0.0.1"
        self.reaper_port = 9999
        self.reaper_receive_port = 9998
        self.console_port = 8001
        self.receive_port = 8000
        self.digico_dispatcher = None
        self.reaper_dispatcher = None
        self.console_client = None
        self.reaper_client = None
        self.digico_osc_server = None
        self.reaper_osc_server = None
        self.name_to_match = ""
        self.is_playing = False
        self.is_recording = False
        self.just_keep_cleaning = True
        self.marker_mode = "PlaybackTrack"
        self.plist_prefs = ""
        self.window_loc = ""
        self.lock = threading.Lock()
        self.check_configuration()
        self.start_threads()
        self.app_window()

    def check_configuration(self):
        # Checking if a .plist config already exists for this app, if not call
        # build_initial_plist
        appname = "Digico-Reaper Link"
        appauthor = "Justin Stasiw"
        config_dir = appdirs.user_config_dir(appname, appauthor)
        if os.path.isdir(config_dir):
            pass
        else:
            os.mkdir(config_dir)
        try:
            self.plist_prefs = config_dir + "/rpdigiprefs.plist"
            with open(self.plist_prefs, 'rb') as fp:
                pl = plistlib.load(fp)
                self.set_vars_from_pref(pl)
        except Exception as e:
            print(e)
            self.build_initial_plist(self.plist_prefs)

    def set_vars_from_pref(self, pl):
        self.console_ip = pl["default_ip"]
        self.local_ip = pl["local_ip"]
        self.console_port = pl["default_digico_send_port"]
        self.receive_port = pl["default_digico_receive_port"]
        self.reaper_port = pl["default_reaper_send_port"]
        self.reaper_receive_port = pl["default_reaper_receive_port"]
        self.window_loc = (pl["window_pos_x"], pl["window_pos_y"])

    def build_initial_plist(self, location_of_plist):
        # Builds a .plist configuration file with default settings.
        p1 = dict(
            default_ip="10.10.13.10",
            local_ip="10.10.13.100",
            default_digico_send_port=8001,
            default_digico_receive_port=8000,
            default_reaper_send_port=9999,
            default_reaper_receive_port=9998,
            window_pos_x=400,
            window_pos_y=222
        )
        with open(location_of_plist, "wb") as fp:
            plistlib.dump(p1, fp)
        with open(self.plist_prefs, 'rb') as fp:
            pl = plistlib.load(fp)
            self.set_vars_from_pref(pl)

    def update_configuration(self, con_ip, local_ip, con_send, con_rcv, rpr_send, rpr_rcv):
        # Given new values from the GUI, update the config file and restart the OSC Server
        with open(self.plist_prefs, 'rb') as fp:
            pl = plistlib.load(fp)
            try:
                pl["default_ip"] = con_ip
                pl["local_ip"] = local_ip
                pl["default_digico_send_port"] = int(con_send)
                pl["default_digico_receive_port"] = int(con_rcv)
                pl["default_reaper_send_port"] = int(rpr_send)
                pl["default_reaper_receive_port"] = int(rpr_rcv)
            except Exception as e:
                print(e)
        with open(self.plist_prefs, 'wb') as fp:
            plistlib.dump(pl, fp)
        self.set_vars_from_pref(pl)
        self.close_servers()
        self.restart_servers()

    def update_pos_in_config(self, win_pos_tuple):
        with open(self.plist_prefs, 'rb') as fp:
            pl = plistlib.load(fp)
            try:
                pl["window_pos_x"] = win_pos_tuple[0]
                pl["window_pos_y"] = win_pos_tuple[1]
            except Exception as e:
                print(e)
        with open(self.plist_prefs, 'wb') as fp:
            plistlib.dump(pl, fp)

    def start_threads(self):
        # Builds the threads for the OSC servers to run in, non-blocking.
        digico_osc_thread = threading.Thread(target=self.build_digico_osc_servers, daemon=False)
        reaper_osc_thread = threading.Thread(target=self.build_reaper_osc_servers, daemon=False)
        osc_cleanup_thread = threading.Thread(target=self.osc_cleanup, daemon=False)
        digico_osc_thread.start()
        reaper_osc_thread.start()
        osc_cleanup_thread.start()

    def build_digico_osc_servers(self):
        # Connect to the Digico console
        self.console_client = udp_client.SimpleUDPClient(self.console_ip, self.console_port)
        self.digico_dispatcher = dispatcher.Dispatcher()
        self.receive_console_OSC()
        self.digico_osc_server = osc_server.ThreadingOSCUDPServer((self.local_ip, self.receive_port),
                                                                  self.digico_dispatcher)
        print("Digico OSC server started.")
        self.digico_osc_server.serve_forever()

    def build_reaper_osc_servers(self):
        # Connect to Reaper via OSC
        self.reaper_client = udp_client.SimpleUDPClient(self.reaper_ip, self.reaper_port)
        self.reaper_dispatcher = dispatcher.Dispatcher()
        self.receive_reaper_OSC()
        self.reaper_osc_server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", self.reaper_receive_port),
                                                                  self.reaper_dispatcher)
        print("Reaper OSC server started")
        self.reaper_osc_server.serve_forever()

    def osc_cleanup(self):
        # Dealing with a memory leak bug in Python's threading server. Threads don't close properly, and so leak memory.
        # This gets called occasionally to clean out dead threads.
        # Can we test to see if this is still required?
        try:
            while self.just_keep_cleaning is True:
                time.sleep(1)
                for thread in self.digico_osc_server._threads:
                    if not thread.is_alive():
                        self.digico_osc_server._threads.remove(thread)
                for thread in self.reaper_osc_server._threads:
                    if not thread.is_alive():
                        self.reaper_osc_server._threads.remove(thread)
        except:
            time.sleep(1)
            self.osc_cleanup()

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
        # Matches an marker composite name with it's Reaper ID
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
        elif playing is False:
            self.is_playing = False
        if recording is True:
            self.is_recording = True
        elif recording is False:
            self.is_recording = False

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

    def request_snapshot_info(self, OSCAddress, CurrentSnapshotNumber):
        # Receives the OSC for the Current Snapshot Number and uses that to request the cue number/name
        self.console_client.send_message("/Snapshots/name/?", CurrentSnapshotNumber)

    def snapshot_OSC_handler(self, OSCAddress, *args):
        # Processes the current cue number
        cue_name = args[3]
        cue_number = str(args[1] / 100)
        if self.marker_mode == "Recording" and self.is_recording is True:
            self.place_marker_at_current()
            self.update_last_marker_name(cue_number + " " + cue_name)
        elif self.marker_mode == "PlaybackTrack" and self.is_playing is False:
            self.get_marker_id_by_name(cue_number + " " + cue_name)

    # GUI Functions:

    def prefs_window(self):
        # Generates the preferences menu GUI in the file menu.
        layout = [
            [sg.Text("Console IP:", font=("Arial", 14))],
            [sg.Input(self.console_ip, size=(15, 1), key="con_ip")],
            [sg.Text("Local IP:", font=("Arial", 14))],
            [sg.Input(self.local_ip, size=(15, 1), key="local_ip")],
            [sg.Text("Digico Ports:", font=("Arial", 14))],
            [sg.Text("Send Port:", font=("Arial", 14)), sg.Text("Receive Port:", font=("Arial", 14))],
            [sg.Text(" "), sg.Input(self.console_port, size=(5, 1), key="con_snd"), sg.Text("     "),
             sg.Input(self.receive_port, size=(5, 1), key="con_rcv")],
            [sg.Text("Reaper Ports:", font=("Arial", 14))],
            [sg.Text("Send Port:", font=("Arial", 14)), sg.Text("Receive Port:", font=("Arial", 14))],
            [sg.Text(" "), sg.Input(self.reaper_port, size=(5, 1), key="rpr_snd"), sg.Text("     "),
             sg.Input(self.reaper_receive_port, size=(5, 1), key="rpr_rcv")],
            [sg.Button('Update', size=(170, 50), font=("Arial", 20))],
        ]

        window = sg.Window("Preferences", layout, location=self.window_loc)
        while True:  # Event Loop
            event, values = window.Read(timeout=400)
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            elif event == "Update":
                self.update_configuration(values["con_ip"], values["local_ip"], values["con_snd"], values["con_rcv"],
                                          values["rpr_snd"], values["rpr_rcv"])
                window.close()

    def app_window(self):
        # Generates the primary program window.
        menu_def = [['&File', ['&Properties', 'E&xit']],
                    ['&Help', '&About...'], ]

        layout = [
            [sg.Text("Select Mode:", font=("Arial", 20))],
            [sg.Radio("Recording", "RADIO1", default=False, key="REC_ENABLE", size_px=(170, 50), font=("Arial", 16))],
            [sg.Radio("Playback Tracking", "RADIO1", default=True, key="PB_TRACK_ENABLE", size_px=(170, 50),
                      font=("Arial", 16))],
            [sg.Radio("Playback No Track", "RADIO1", default=False, key="PB_TRACK_DISABLE", size_px=(170, 50),
                      font=("Arial", 16))],
            [sg.Button('Exit', size=(170, 50), font=("Arial", 20))],
            [sg.Menu(menu_def, tearoff=False, pad=(200, 1))]

        ]
        window = sg.Window("Digico-Reaper Link", layout, location=self.window_loc)
        while True:  # Event Loop
            event, values = window.Read(timeout=400)
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            elif event == "Properties":
                self.prefs_window()
            if values["REC_ENABLE"] is True and values["PB_TRACK_ENABLE"] is False and values["PB_TRACK_DISABLE"] is False:
                self.marker_mode = "Recording"
            elif values["REC_ENABLE"] is False and values["PB_TRACK_ENABLE"] is True and values["PB_TRACK_DISABLE"] is False:
                self.marker_mode = "PlaybackTrack"
            elif values["REC_ENABLE"] is False and values["PB_TRACK_ENABLE"] is False and values["PB_TRACK_DISABLE"] is True:
                self.marker_mode = "PlaybackNoTrack"
        self.update_pos_in_config(window.CurrentLocation())
        window.Close()
        self.close_servers()
        sys.exit()

    def close_servers(self):
        # Shutdown the OSC servers, do not close the app.
        try:
            self.digico_osc_server.shutdown()
            self.digico_osc_server.server_close()
        except Exception as e:
            print(e)
        try:
            self.reaper_osc_server.shutdown()
            self.reaper_osc_server.server_close()
        except Exception as e:
            print(e)
        try:
            self.just_keep_cleaning = False
        except Exception as e:
            print(e)

    def restart_servers(self):
        # Restart the OSC server threads.
        self.start_threads()


if __name__ == "__main__":
    ReaperDigicoOSCBridge()
