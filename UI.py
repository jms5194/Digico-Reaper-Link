import PySimpleGUI as sg
import sys
import UI


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
        [sg.Button('Update', size=(20, 1), font=("Arial", 20))],
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
        [sg.Radio("Recording", "RADIO1", default=False, key="REC_ENABLE", font=("Arial", 16))],
        [sg.Radio("Playback Tracking", "RADIO1", default=True, key="PB_TRACK_ENABLE",
                  font=("Arial", 16))],
        [sg.Radio("Playback No Track", "RADIO1", default=False, key="PB_TRACK_DISABLE",
                  font=("Arial", 16))],
        [sg.Button('Exit', size=(20, 1), font=("Arial", 20))],
        [sg.Menu(menu_def, tearoff=False, pad=(200, 1))]

    ]
    window = sg.Window("Digico-Reaper Link", layout, location=self.window_loc)
    while True:  # Event Loop
        event, values = window.Read(timeout=400)
        if event == sg.WIN_CLOSED or event == 'Exit':
            break
        elif event == "Properties":
            UI.prefs_window(self)
        if values["REC_ENABLE"] is True and values["PB_TRACK_ENABLE"] is False and values["PB_TRACK_DISABLE"] is False:
            self.marker_mode = "Recording"
        elif values["REC_ENABLE"] is False and values["PB_TRACK_ENABLE"] is True and values[
            "PB_TRACK_DISABLE"] is False:
            self.marker_mode = "PlaybackTrack"
        elif values["REC_ENABLE"] is False and values["PB_TRACK_ENABLE"] is False and values[
            "PB_TRACK_DISABLE"] is True:
            self.marker_mode = "PlaybackNoTrack"
    self.update_pos_in_config(window.CurrentLocation())
    window.Close()
    self.close_servers()
    sys.exit()
