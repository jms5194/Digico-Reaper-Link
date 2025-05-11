import threading

import wx
import ipaddress
from app_settings import settings
from utilities import ReaperDigicoOSCBridge
from pubsub import pub


class MainWindow(wx.Frame):
    # Bringing the logic from utilities as an attribute of MainWindow
    BridgeFunctions = ReaperDigicoOSCBridge()

    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="Digico-Reaper Link")
        self.SetPosition(settings.window_loc)
        self.SetSize(settings.window_size)
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
        # Let's close the window and destroy the UI
        # But let's remember where we left the window for next time
        cur_pos = self.GetTopLevelParent().GetPosition()
        cur_size = self.GetTopLevelParent().GetSize()
        self.GetTopLevelParent().BridgeFunctions.update_pos_in_config(cur_pos)
        self.GetTopLevelParent().BridgeFunctions.update_size_in_config(cur_size)
        # Make a dialog to confirm closing.
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
    # This is our main window UI
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.DigicoTimer = None
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        # Font Definitions
        header_font = wx.Font(20, family=wx.FONTFAMILY_SWISS, style=0, weight=wx.FONTWEIGHT_BOLD,
                              underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        sub_header1_font = wx.Font(17, family=wx.FONTFAMILY_SWISS, style=0, weight=wx.FONTWEIGHT_NORMAL,
                                   underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        sub_header2_font = wx.Font(14, family=wx.FONTFAMILY_SWISS, style=0, weight=wx.FONTWEIGHT_NORMAL,
                                   underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        # Button grid for application mode
        radio_grid = wx.GridSizer(3, 1, 0, 0)
        self.rec_button_cntl = wx.RadioButton(self, label="Recording", style=wx.RB_GROUP)
        self.rec_button_cntl.SetFont(header_font)
        radio_grid.Add(self.rec_button_cntl, 0, wx.ALL | wx.EXPAND, 5)
        self.track_button_cntl = wx.RadioButton(self, label="Playback Tracking")
        self.track_button_cntl.SetValue(True)
        self.track_button_cntl.SetFont(header_font)
        radio_grid.Add(self.track_button_cntl, 0, wx.ALL | wx.EXPAND, 5)
        self.notrack_button_cntl = wx.RadioButton(self, label="Playback No Track")
        self.notrack_button_cntl.SetFont(header_font)
        radio_grid.Add(self.notrack_button_cntl, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(radio_grid, 0, wx.ALL | wx.EXPAND, 5)

        # Is connected section:
        connected_status = wx.StaticText(self)
        connected_status.SetLabel("Connection Status")
        connected_status.SetFont(sub_header1_font)

        connected_grid = wx.GridSizer(3, 1, 5, 5)

        digico_con_label = wx.StaticText(self)
        digico_con_label.SetLabel("Digico")
        digico_con_label.SetFont(sub_header2_font)
        connected_grid.Add(digico_con_label, flag=wx.ALIGN_CENTER_HORIZONTAL)

        self.digico_connected = wx.TextCtrl(self, size=wx.Size(100, -1), style=wx.TE_CENTER)
        self.digico_connected.SetLabel("N/C")
        self.digico_connected.SetEditable(False)
        self.digico_connected.SetBackgroundColour(wx.RED)
        connected_grid.Add(self.digico_connected, flag=wx.ALIGN_CENTER_HORIZONTAL)

        panel_sizer.Add(connected_status, flag=wx.ALIGN_CENTER_HORIZONTAL)
        panel_sizer.Add(connected_grid, flag=wx.ALIGN_CENTER_HORIZONTAL)

        # Lower Buttons
        button_grid = wx.GridSizer(3, 1, 10, 10)
        # Drop Marker Button
        marker_button = wx.Button(self, label="Drop Marker")
        button_grid.Add(marker_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        # Attempt Reconnect Button
        attempt_reconnect_button = wx.Button(self, label="Attempt Reconnect")
        button_grid.Add(attempt_reconnect_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        # Exit Button
        exit_button = wx.Button(self, label="Exit")
        button_grid.Add(exit_button, flag=wx.ALIGN_CENTER_HORIZONTAL)
        panel_sizer.Add(button_grid, flag=wx.ALIGN_CENTER_HORIZONTAL)
        panel_sizer.AddSpacer(15)
        self.SetSizer(panel_sizer)
        # Bindings
        self.Bind(wx.EVT_BUTTON, self.place_marker, marker_button)
        self.Bind(wx.EVT_BUTTON, self.exitapp, exit_button)
        self.Bind(wx.EVT_BUTTON, self.attemptreconnect, attempt_reconnect_button)
        self.Bind(wx.EVT_RADIOBUTTON, self.recmode, self.rec_button_cntl)
        self.Bind(wx.EVT_RADIOBUTTON, self.trackmode, self.track_button_cntl)
        self.Bind(wx.EVT_RADIOBUTTON, self.notrackmode, self.notrack_button_cntl)
        # Subscribing to the OSC response for console name to reset the timeout timer
        pub.subscribe(self.digico_connected_listener, "console_name")
        pub.subscribe(self.reaper_disconnected_listener, "reaper_error")
        pub.subscribe(self.callforreaperrestart, "reset_reaper")
        pub.subscribe(self.update_mode_select_gui_from_osc, "mode_select_osc")
        if MainWindow.BridgeFunctions.ValidateReaperPrefs():
            MainWindow.BridgeFunctions.start_threads()
        # Start a timer for Digico timeout
        self.timer_lock = threading.Lock()
        self.configuretimers()

    @staticmethod
    def place_marker(e):
        # Manually places a marker in Reaper from the UI
        MainWindow.BridgeFunctions.place_marker_at_current()
        MainWindow.BridgeFunctions.update_last_marker_name("Marker from UI")

    def exitapp(self, e):
        # Calls on_close for the parent window
        self.GetTopLevelParent().on_close(None)

    def update_mode_select_gui_from_osc(self, selected_mode):
        if selected_mode == "Recording":
            wx.CallAfter(self.rec_button_cntl.SetValue, True)
        elif selected_mode == "PlaybackTrack":
            wx.CallAfter(self.track_button_cntl.SetValue, True)
        elif selected_mode == "PlaybackNoTrack":
            wx.CallAfter(self.notrack_button_cntl.SetValue, True)

    @staticmethod
    def recmode(e):
        settings.marker_mode = "Recording"

    @staticmethod
    def trackmode(e):
        settings.marker_mode = "PlaybackTrack"

    @staticmethod
    def notrackmode(e):
        settings.marker_mode = "PlaybackNoTrack"

    def configuretimers(self):
        # Builds a 5-second non-blocking timer for console response timeout.
        # Calls self.digico_disconnected if timer runs out.
        with self.timer_lock:
            if self.DigicoTimer and self.DigicoTimer.IsRunning():
                self.DigicoTimer.Stop()
            self.DigicoTimer = wx.CallLater(5000, self.digico_disconnected)
            wx.CallAfter(self.DigicoTimer.Start)

    def digico_connected_listener(self, consolename, arg2=None):
        if self.DigicoTimer.IsRunning():
            # When a response is received from the console, reset the timeout timer if running
            wx.CallAfter(self.DigicoTimer.Stop)
            # Update the UI to reflect the connected status
            wx.CallAfter(self.digico_connected.SetLabel, consolename)
            wx.CallAfter(self.digico_connected.SetBackgroundColour,wx.GREEN)
            # Restart the timeout timer
            self.configuretimers()

        else:
            # If the timer was not already running
            # Update UI to reflect connected
            wx.CallAfter(self.digico_connected.SetLabel,consolename)
            wx.CallAfter(self.digico_connected.SetBackgroundColour,wx.GREEN)
            # Start the timer
            self.configuretimers()


    def digico_disconnected(self):
        # If timer runs out without being reset, update the UI to N/C
        wx.CallAfter(self.digico_connected.SetLabel,"N/C")
        wx.CallAfter(self.digico_connected.SetBackgroundColour,wx.RED)

    def reaper_disconnected_listener(self, reapererror, arg2=None):
        dlg = wx.MessageDialog(self,
                               "Reaper is not currently open. Please open and press OK.",
                               "Reaper Disconnected", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_CANCEL:
            closed_complete = self.GetTopLevelParent().BridgeFunctions.close_servers()
            if closed_complete:
                try:
                    self.GetTopLevelParent().Destroy()
                except Exception as e:
                    print(e)
        elif result == wx.ID_OK:
            if MainWindow.BridgeFunctions.ValidateReaperPrefs():
                MainWindow.BridgeFunctions.start_threads()

    def callforreaperrestart(self, resetreaper, arg2=None):
        dlg = wx.MessageDialog(self,
                               "Reaper has been configured for use with Digico-Reaper Link. "
                               "Please restart Reaper and press OK",
                               "Reaper Configured", wx.OK | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def attemptreconnect(e):
        # Just forces a close/reconnect of the OSC servers by manually updating the configuration.
        MainWindow.BridgeFunctions.update_configuration(con_ip=settings.console_ip,
                                                        rptr_ip="127.0.0.1", con_send=settings.console_port,
                                                        con_rcv=settings.receive_port,
                                                        fwd_enable=settings.forwarder_enabled,
                                                        rpr_send=settings.reaper_port,
                                                        rpr_rcv=settings.reaper_receive_port,
                                                        rptr_snd=settings.repeater_port,
                                                        rptr_rcv=settings.repeater_receive_port)


class PrefsWindow(wx.Frame):
    # This is our preferences window pane
    def __init__(self, title, parent):
        wx.Frame.__init__(self, parent=parent, size=wx.Size(400, 600), title=title)
        panel = PrefsPanel(parent=wx.GetTopLevelParent(self))
        self.Fit()
        self.Show()


class PrefsPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        # Define Fonts:
        self.ip_inspected = False
        header_font = wx.Font(20, family=wx.FONTFAMILY_MODERN, style=0, weight=wx.FONTWEIGHT_BOLD,
                              underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        sub_header_font = wx.Font(16, family=wx.FONTFAMILY_MODERN, style=0, weight=wx.FONTWEIGHT_BOLD,
                                  underline=False, faceName="", encoding=wx.FONTENCODING_DEFAULT)
        base_font = wx.Font(12, family=wx.FONTFAMILY_MODERN, style=0, weight=wx.FONTWEIGHT_NORMAL,
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
        panel_sizer.AddSpacer(15)
        self.SetSizer(panel_sizer)
        self.Fit()

        # Prefs Window Bindings
        self.Bind(wx.EVT_BUTTON, self.update_button_pressed, update_button)
        self.console_ip_control.Bind(wx.EVT_TEXT, self.changed_console_ip)
        self.console_ip_control.Bind(wx.EVT_KILL_FOCUS, self.check_console_ip)
        self.Show()

    def update_button_pressed(self, e):
        # Writing the new values from the preferences panel to settings.py
        settings.console_ip = self.console_ip_control.GetValue()
        settings.console_port = str(self.digico_send_port_control.GetValue())
        settings.receive_port = str(self.digico_rcv_port_control.GetValue())
        settings.repeater_port = str(self.repeater_send_port_control.GetValue())
        settings.repeater_receive_port = str(self.repeater_rcv_port_control.GetValue())
        if self.repeater_radio_enabled.GetValue() is True:
            settings.forwarder_enabled = "True"
        elif self.repeater_radio_enabled.GetValue() is False:
            settings.forwarder_enabled = "False"
        # Force a close/reconnect of the OSC servers by pushing the configuration update.
        MainWindow.BridgeFunctions.update_configuration(con_ip=settings.console_ip,
                                                        rptr_ip="127.0.0.1", con_send=settings.console_port,
                                                        con_rcv=settings.receive_port,
                                                        fwd_enable=settings.forwarder_enabled,
                                                        rpr_send=settings.reaper_port,
                                                        rpr_rcv=settings.reaper_receive_port,
                                                        rptr_snd=settings.repeater_port,
                                                        rptr_rcv=settings.repeater_receive_port)
        # Close the preferences window when update is pressed.
        self.Parent.Destroy()

    def changed_console_ip(self, e):
        # Flag to know if the console IP has been modified in the prefs window
        self.ip_inspected = False

    def check_console_ip(self, e):
        # Validates input into the console IP address field
        # Use the ip_address function from the ipaddress module to check if the input is a valid IP address
        ip = self.console_ip_control.GetValue()

        if not self.ip_inspected:
            self.ip_inspected = True
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                # If the input is not a valid IP address, catch the exception and show a dialog
                dlg = wx.MessageDialog(self, "This is not a valid IP address for the console. Please try again",
                                       "Digico-Reaper Link", wx.OK)
                dlg.ShowModal()  # Shows it
                dlg.Destroy()  # Destroy pop-up when finished.
                # Put the focus back on the bad field
                wx.CallAfter(self.console_ip_control.SetFocus)


if __name__ == "__main__":
    app = wx.App(False)
    frame = MainWindow()
    app.MainLoop()
