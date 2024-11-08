import wx
import ipaddress
import settings
from utilities import ReaperDigicoOSCBridge
from pubsub import pub


class MainWindow(wx.Frame):
    # Bringing the logic from main as an attribute of MainWindow
    BridgeFunctions = ReaperDigicoOSCBridge()

    def __init__(self):
        wx.Frame.__init__(self, parent=None, size=(221, 310), title="Digico-Reaper Link")
        self.SetPosition(settings.window_loc)
        panel = MainPanel(self)
        # Build a menubar:

        filemenu = wx.Menu()
        about_menuitem = filemenu.Append(wx.ID_ABOUT, "&About", "Info about this program")
        filemenu.AppendSeparator()
        m_exit = filemenu.Append(wx.ID_EXIT, "&Exit\tAlt-X", "Close window and exit program.")
        properties_menuitem = filemenu.Append(wx.ID_PROPERTIES, "Properties", "Program Settings")
        menubar = wx.MenuBar()
        menubar.Append(filemenu, "&File")
        self.SetMenuBar(menubar)

        # Main Window Bindings
        self.Bind(wx.EVT_MENU, self.on_close, m_exit)
        self.Bind(wx.EVT_MENU, self.on_about, about_menuitem)
        self.Bind(wx.EVT_MENU, self.launch_prefs, properties_menuitem)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.Show()

    def on_about(self, event):
        # Create the About Dialog Box
        dlg = wx.MessageDialog(self, " An OSC Translation tool for Digico and Reaper. Written by Justin Stasiw. ",
                               "Digico-Reaper Link", wx.OK)
        dlg.ShowModal()  # Shows it
        dlg.Destroy()  # Destroy pop-up when finished.

    def launch_prefs(self, event):
        # Open the preferences frame
        PrefsWindow(parent=wx.GetTopLevelParent(self), title="Digico-Reaper Properties")

    def on_close(self, event):
        cur_pos = self.GetTopLevelParent().GetPosition()
        self.GetTopLevelParent().BridgeFunctions.update_pos_in_config(cur_pos)
        dlg = wx.MessageDialog(self,
                               "Do you really want to close Digico-Reaper Link?",
                               "Confirm Exit", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            closed_complete = self.GetTopLevelParent().BridgeFunctions.close_servers()
            if closed_complete:
                try:
                    self.GetTopLevelParent().Destroy()
                except Exception as e:
                    print(e)


class MainPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        header_font = wx.Font(20, family=wx.FONTFAMILY_SWISS, style=0, weight=wx.BOLD, underline=False, faceName="",
                              encoding=wx.FONTENCODING_DEFAULT)
        sub_header1_font = wx.Font(17,family=wx.FONTFAMILY_SWISS, style=0, weight=wx.NORMAL, underline=False, faceName="",
                              encoding=wx.FONTENCODING_DEFAULT)
        sub_header2_font =  wx.Font(14,family=wx.FONTFAMILY_SWISS, style=0, weight=wx.NORMAL, underline=False, faceName="",
                              encoding=wx.FONTENCODING_DEFAULT)
        radio_grid = wx.GridSizer(3, 1, 0, 0)
        rec_button_cntl = wx.RadioButton(self, label="Recording", style=wx.RB_GROUP)
        rec_button_cntl.SetFont(header_font)
        radio_grid.Add(rec_button_cntl, 0, wx.ALL | wx.EXPAND, 5)
        track_button_cntl = wx.RadioButton(self, label="Playback Tracking")
        track_button_cntl.SetValue(True)
        track_button_cntl.SetFont(header_font)
        radio_grid.Add(track_button_cntl, 0, wx.ALL | wx.EXPAND, 5)
        notrack_button_cntl = wx.RadioButton(self, label="Playback No Track")
        notrack_button_cntl.SetFont(header_font)
        radio_grid.Add(notrack_button_cntl, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(radio_grid, 0, wx.ALL | wx.EXPAND, 5)

        # Is connected section:
        connected_status = wx.StaticText(self)
        connected_status.SetLabel("Connection Status")
        connected_status.SetFont(sub_header1_font)

        connected_grid = wx.GridSizer(3,1,5,5)

        digico_con_label = wx.StaticText(self)
        digico_con_label.SetLabel("Digico")
        digico_con_label.SetFont(sub_header2_font)
        connected_grid.Add(digico_con_label, flag=wx.ALIGN_CENTER_HORIZONTAL)

        self.digico_connected = wx.TextCtrl(self, size=(100, -1), style=wx.TE_CENTER)
        self.digico_connected.SetLabel("N/C")
        self.digico_connected.SetEditable(False)
        self.digico_connected.SetBackgroundColour("Red")
        connected_grid.Add(self.digico_connected, flag=wx.ALIGN_CENTER_HORIZONTAL)

        panel_sizer.Add(connected_status, flag=wx.ALIGN_CENTER_HORIZONTAL)
        panel_sizer.Add(connected_grid, flag=wx.ALIGN_CENTER_HORIZONTAL)

        #Lower Buttons
        button_grid = wx.GridSizer(3,1,10,10)
        # Drop Marker Button
        marker_button = wx.Button(self, label ="Drop Marker")
        button_grid.Add(marker_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        # Attempt Reconnect Button
        attempt_reconnect_button = wx.Button(self, label="Attempt Reconnect")
        button_grid.Add(attempt_reconnect_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        # Exit Button
        exit_button = wx.Button(self, label="Exit")
        button_grid.Add(exit_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        panel_sizer.Add(button_grid,flag=wx.ALIGN_CENTER_HORIZONTAL )
        self.SetSizer(panel_sizer)
        # Bindings
        self.Bind(wx.EVT_BUTTON, self.place_marker, marker_button)
        self.Bind(wx.EVT_BUTTON, self.exitapp, exit_button)
        self.Bind(wx.EVT_CLOSE, self.exitapp)
        self.Bind(wx.EVT_BUTTON, self.attemptreconnect, attempt_reconnect_button)
        self.Bind(wx.EVT_RADIOBUTTON, self.recmode, rec_button_cntl)
        self.Bind(wx.EVT_RADIOBUTTON, self.trackmode, track_button_cntl)
        self.Bind(wx.EVT_RADIOBUTTON, self.notrackmode, notrack_button_cntl)

        pub.subscribe(self.digico_connected_listener, "console_name")
        self.configuretimers()

    def place_marker(self, e):
        MainWindow.BridgeFunctions.place_marker_at_current()
        MainWindow.BridgeFunctions.update_last_marker_name("Marker from UI")

    def exitapp(self, e):
        self.GetTopLevelParent().on_close(None)

    def recmode(self, e):
        settings.marker_mode = "Recording"

    def trackmode(self, e):
        settings.marker_mode = "PlaybackTrack"

    def notrackmode(self, e):
        settings.marker_mode = "PlaybackNoTrack"

    def configuretimers(self):
        self.DigicoTimer = wx.CallLater(5000, self.digico_disconnected)

    def digico_connected_listener(self, consolename, arg2=None):
        if self.DigicoTimer.IsRunning():
            self.DigicoTimer.Stop()
            self.digico_connected.SetLabel(consolename)
            self.digico_connected.SetBackgroundColour("Green")
            wx.CallAfter(self.DigicoTimer.Start)
        else:
            self.digico_connected.SetLabel(consolename)
            self.digico_connected.SetBackgroundColour("Green")
            wx.CallAfter(self.DigicoTimer.Start)

    def digico_disconnected(self):
        self.digico_connected.SetLabel("N/C")
        self.digico_connected.SetBackgroundColour("Red")

    def attemptreconnect(self, e):
        MainWindow.BridgeFunctions.update_configuration(con_ip=settings.console_ip, local_ip=settings.local_ip,
                                                        rptr_ip="127.0.0.1", con_send=settings.console_port,
                                                        con_rcv=settings.receive_port,
                                                        fwd_enable=settings.forwarder_enabled,
                                                        rpr_send=settings.reaper_port,
                                                        rpr_rcv=settings.reaper_receive_port,
                                                        rptr_snd=settings.repeater_port,
                                                        rptr_rcv=settings.repeater_receive_port)


class PrefsWindow(wx.Frame):
    def __init__(self, title, parent):
        wx.Frame.__init__(self, parent=parent, size=(400, 600), title=title)
        panel = PrefsPanel(parent=wx.GetTopLevelParent(self))
        self.Show()


class PrefsPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        header_font = wx.Font(20, family=wx.FONTFAMILY_MODERN, style=0, weight=wx.BOLD,
                              underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        sub_header_font = wx.Font(16, family=wx.FONTFAMILY_MODERN, style=0, weight=wx.BOLD,
                                  underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        base_font = wx.Font(12, family=wx.FONTFAMILY_MODERN, style=0, weight=wx.NORMAL,
                            underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        # Console IP Label
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        console_ip_text = wx.StaticText(self, label="Console IP", style=wx.ALIGN_CENTER)
        console_ip_text.SetFont(header_font)
        panel_sizer.Add(console_ip_text, 0, wx.ALL | wx.EXPAND, 5)
        # Console IP Input
        self.console_ip_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.console_ip_control.SetMaxLength(15)
        self.console_ip_control.SetValue(settings.console_ip)
        panel_sizer.Add(self.console_ip_control, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(0, 10)
        # Local IP Label
        local_ip_text = wx.StaticText(self, label="Local IP", style=wx.ALIGN_CENTER)
        local_ip_text.SetFont(header_font)
        panel_sizer.Add(local_ip_text, 0, wx.ALL | wx.EXPAND, 5)
        # Local IP Input
        self.local_ip_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.local_ip_control.SetValue(settings.local_ip)
        panel_sizer.Add(self.local_ip_control, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(0, 25)
        # Digico Ports Label
        digico_ports_text = wx.StaticText(self, label="Digico Ports", style=wx.ALIGN_CENTER)
        digico_ports_text.SetFont(header_font)
        panel_sizer.Add(digico_ports_text, 0, wx.ALL | wx.EXPAND, 1)
        # Digico Ports Input
        digico_ports_grid = wx.GridSizer(2, 2, -1, 10)
        digico_send_port_text = wx.StaticText(self, label="Send to Console", style=wx.ALIGN_CENTER)
        digico_send_port_text.SetFont(base_font)
        digico_ports_grid.Add(digico_send_port_text, 0, wx.ALL | wx.EXPAND, 5)
        digico_rcv_port_text = wx.StaticText(self, label="Receive from Console", style=wx.ALIGN_CENTER)
        digico_rcv_port_text.SetFont(base_font)
        digico_ports_grid.Add(digico_rcv_port_text, 0, wx.ALL | wx.EXPAND, 5)
        self.digico_send_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.digico_send_port_control.SetMaxLength(5)
        self.digico_send_port_control.SetValue(str(settings.console_port))
        digico_ports_grid.Add(self.digico_send_port_control, 0, wx.ALL | wx.EXPAND, -1)
        self.digico_rcv_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.digico_rcv_port_control.SetMaxLength(5)
        self.digico_rcv_port_control.SetValue(str(settings.receive_port))
        digico_ports_grid.Add(self.digico_rcv_port_control, 0, wx.ALL | wx.EXPAND, -1)
        panel_sizer.Add(digico_ports_grid, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(0, 25)

        # OSC Repeater Label
        osc_repeater_text = wx.StaticText(self, label="OSC Repeater", style=wx.ALIGN_CENTER)
        osc_repeater_text.SetFont(header_font)
        panel_sizer.Add(osc_repeater_text, 0, wx.ALL | wx.EXPAND, 5)
        repeater_radio_grid = wx.GridSizer(1, 2, 0, 0)
        self.repeater_radio_enabled = wx.RadioButton(self, label="Repeater Enabled", style=wx.RB_GROUP)
        repeater_radio_grid.Add(self.repeater_radio_enabled, 0, wx.ALL | wx.EXPAND, 5)
        self.repeater_radio_enabled.SetValue(settings.forwarder_enabled == "True")
        self.repeater_radio_disabled = wx.RadioButton(self, label="Repeater Disabled")
        repeater_radio_grid.Add(self.repeater_radio_disabled, 0, wx.ALL | wx.EXPAND, 5)
        self.repeater_radio_disabled.SetValue(settings.forwarder_enabled == "False")
        panel_sizer.Add(repeater_radio_grid, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(0, 10)
        # Repeater Ports Label
        repeater_ports_text = wx.StaticText(self, label="Repeater Ports", style=wx.ALIGN_CENTER)
        repeater_ports_text.SetFont(sub_header_font)
        panel_sizer.Add(repeater_ports_text, 0, wx.ALL | wx.EXPAND, -1)
        # Repeater Ports Input
        repeater_ports_grid = wx.GridSizer(2, 2, -1, 10)
        repeater_send_port_text = wx.StaticText(self, label="Send to Device", style=wx.ALIGN_CENTER)
        repeater_send_port_text.SetFont(base_font)
        repeater_ports_grid.Add(repeater_send_port_text, 0, wx.ALL | wx.EXPAND, 5)
        repeater_rcv_port_text = wx.StaticText(self, label="Receive from Device", style=wx.ALIGN_CENTER)
        repeater_rcv_port_text.SetFont(base_font)
        repeater_ports_grid.Add(repeater_rcv_port_text, 0, wx.ALL | wx.EXPAND, 5)
        self.repeater_send_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.repeater_send_port_control.SetMaxLength(5)
        self.repeater_send_port_control.SetValue(str(settings.repeater_port))
        repeater_ports_grid.Add(self.repeater_send_port_control, 0, wx.ALL | wx.EXPAND, -1)
        self.repeater_rcv_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.repeater_rcv_port_control.SetMaxLength(5)
        self.repeater_rcv_port_control.SetValue(str(settings.repeater_receive_port))
        repeater_ports_grid.Add(self.repeater_rcv_port_control, 0, wx.ALL | wx.EXPAND, -1)
        panel_sizer.Add(repeater_ports_grid, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(0, 25)
        # Update Button
        update_button = wx.Button(self, -1, "Update")
        panel_sizer.Add(update_button, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(panel_sizer)

        # Prefs Window Bindings
        self.Bind(wx.EVT_BUTTON, self.update_button_pressed, update_button)
        self.Show()

    def update_button_pressed(self, e):
        settings.console_ip = self.console_ip_control.GetValue()
        settings.local_ip = self.local_ip_control.GetValue()
        settings.console_port = str(self.digico_send_port_control.GetValue())
        settings.receive_port = str(self.digico_rcv_port_control.GetValue())
        settings.repeater_port = str(self.repeater_send_port_control.GetValue())
        settings.repeater_receive_port = str(self.repeater_rcv_port_control.GetValue())
        if self.repeater_radio_enabled is True:
            settings.forwarder_enabled = "True"
        elif self.repeater_radio_enabled is False:
            settings.forwarder_enabled = "False"
        MainWindow.BridgeFunctions.update_configuration(con_ip=settings.console_ip, local_ip=settings.local_ip,
                                                        rptr_ip="127.0.0.1", con_send=settings.console_port,
                                                        con_rcv=settings.receive_port,
                                                        fwd_enable=settings.forwarder_enabled,
                                                        rpr_send=settings.reaper_port,
                                                        rpr_rcv=settings.reaper_receive_port,
                                                        rptr_snd=settings.repeater_port,
                                                        rptr_rcv=settings.repeater_receive_port)
        self.Parent.Destroy()

    def check_ip(self, ip):
        # Use the ip_address function from the ipaddress module to check if the input is a valid IP address
        try:
            ipaddress.ip_address(ip)
            print("Valid IP address")
        except ValueError:
            # If the input is not a valid IP address, catch the exception and print an error message
            print("Invalid IP address")


if __name__ == "__main__":
    app = wx.App(False)
    frame = MainWindow()
    app.MainLoop()
