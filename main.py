import ipaddress
import threading

import wx
from pubsub import pub

from app_settings import settings
from consoles import CONSOLES, Console, Feature
from daws import Daw
from logger_config import logger
from utilities import DawConsoleBridge


class MainWindow(wx.Frame):
    # Bringing the logic from utilities as an attribute of MainWindow
    BridgeFunctions = DawConsoleBridge()

    def __init__(self):
        logger.info("Initializing main window")
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
        PrefsWindow(parent=wx.GetTopLevelParent(self), title="Digico-Reaper Properties", console=self.GetTopLevelParent().BridgeFunctions.console)

    def on_close(self, event):
        # Let's close the window and destroy the UI
        # But let's remember where we left the window for next time
        logger.info("Closing Application")
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
                    logger.error(f"Error closing application: {e}")


class MainPanel(wx.Panel):
    # This is our main window UI
    def __init__(self, parent):
        logger.info("Initializing main panel")
        wx.Panel.__init__(self, parent)
        self.DigicoTimer: wx.CallLater | None = None
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

        self.console_type_connection_label = wx.StaticText(self)
        self.console_type_connection_label.SetLabel(MainWindow.BridgeFunctions.console.type)
        self.console_type_connection_label.SetFont(sub_header2_font)
        connected_grid.Add(self.console_type_connection_label, flag=wx.ALIGN_CENTER_HORIZONTAL)

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
        pub.subscribe(self.console_connected, "console_connected")
        pub.subscribe(self.console_disconnected, "console_disconnected")
        pub.subscribe(self.console_type_updated, "console_type_updated")
        pub.subscribe(self.reaper_disconnected_listener, "reaper_error")
        pub.subscribe(self.callforreaperrestart, "reset_reaper")
        pub.subscribe(self.update_mode_select_gui_from_osc, "mode_select_osc")
        MainWindow.BridgeFunctions.start_threads()
        # Start a timer for Digico timeout
        self.timer_lock = threading.Lock()
        self.configuretimers()

    @staticmethod
    def place_marker(e):
        # Manually places a marker in Reaper from the UI
        pub.sendMessage("place_marker_with_name", marker_name="Marker from UI")

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
        # Calls self.console_disconnected if timer runs out.
        with self.timer_lock:
            def safe_timer_config():
                if self.DigicoTimer and self.DigicoTimer.IsRunning():
                    self.DigicoTimer.Stop()
                self.DigicoTimer = wx.CallLater(5000, self.console_disconnected)
                self.DigicoTimer.Start()
            wx.CallAfter(safe_timer_config)

    def console_type_updated(self, console: Console) -> None:
        wx.CallAfter(self.console_type_connection_label.SetLabel, console.type)

    def console_connected(self, consolename, colour: wx.Colour = wx.GREEN):
        if isinstance(self.DigicoTimer, wx.CallLater) and self.DigicoTimer.IsRunning():
            # When a response is received from the console, reset the timeout timer if running
            wx.CallAfter(self.DigicoTimer.Stop)
            # Update the UI to reflect the connected status
            self.digico_connected.SetLabel(consolename)
            self.digico_connected.SetBackgroundColour(colour)
            self.digico_connected.SetForegroundColour(wx.BLACK)
            # Restart the timeout timer
            self.configuretimers()

        else:
            # If the timer was not already running
            # Update UI to reflect connected
            wx.CallAfter(self.digico_connected.SetLabel,consolename)
            wx.CallAfter(self.digico_connected.SetBackgroundColour,wx.GREEN)
            # Start the timer
            self.configuretimers()


    def console_disconnected(self):
        # If timer runs out without being reset, update the UI to N/C
        self.digico_connected.SetLabel("N/C")
        self.digico_connected.SetBackgroundColour(wx.RED)
        self.digico_connected.SetForegroundColour(wx.WHITE)

    def reaper_disconnected_listener(self, reapererror, arg2=None):
        logger.info("Reaper not connected. Reporting to user.")
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
                    logger.error(f"Failed to close Reaper disconnected dialog: {e}")
        elif result == wx.ID_OK:
            MainWindow.BridgeFunctions.start_threads()

    def callforreaperrestart(self, resetreaper, arg2=None):
        logger.info("Reaper has been configured. Requesting restart")
        dlg = wx.MessageDialog(self,
                               "Reaper has been configured for use with Digico-Reaper Link. "
                               "Please restart Reaper and press OK",
                               "Reaper Configured", wx.OK | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def attemptreconnect(e):
        logger.info("Manual reconnection requested.")
        # Just forces a close/reconnect of the OSC servers by manually updating the configuration.
        MainWindow.BridgeFunctions.update_configuration(con_ip=settings.console_ip,
                                                        rptr_ip=settings.repeater_ip, con_send=settings.console_port,
                                                        con_rcv=settings.receive_port,
                                                        fwd_enable=settings.forwarder_enabled,
                                                        rpr_send=settings.reaper_port,
                                                        rpr_rcv=settings.reaper_receive_port,
                                                        rptr_snd=settings.repeater_port,
                                                        rptr_rcv=settings.repeater_receive_port,
                                                        name_only=settings.name_only_match,
                                                        console_type=settings.console_type,
                                                        daw_type=settings.daw_type)


class PrefsWindow(wx.Frame):
    # This is our preferences window pane
    def __init__(self, title, parent, console: Console):
        logger.info("Creating PrefsWindow")
        wx.Frame.__init__(self, parent=parent, size=wx.Size(400, 800), title=title)
        panel = PrefsPanel(parent=wx.GetTopLevelParent(self), console=console)
        self.Fit()
        self.Show()


class PrefsPanel(wx.Panel):
    def __init__(self, parent, console: Console):
        logger.info("Creating PrefsPanel")
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
        # Console Ports Label
        console_ports_text = wx.StaticText(self, label="Console Connection Ports", style=wx.ALIGN_CENTER)
        console_ports_text.SetFont(header_font)
        panel_sizer.Add(console_ports_text, 0, wx.ALL | wx.EXPAND, 1)
        # Console Ports Input
        console_ports_grid = wx.GridSizer(2, 2, -1, 10)
        console_send_port_text = wx.StaticText(self, label="Send to Console", style=wx.ALIGN_CENTER)
        console_send_port_text.SetFont(base_font)
        console_ports_grid.Add(console_send_port_text, 0, wx.ALL | wx.EXPAND, 5)
        console_rcv_port_text = wx.StaticText(self, label="Receive from Console", style=wx.ALIGN_CENTER)
        console_rcv_port_text.SetFont(base_font)
        console_ports_grid.Add(console_rcv_port_text, 0, wx.ALL | wx.EXPAND, 5)
        self.console_send_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.console_send_port_control.SetMaxLength(5)
        self.console_send_port_control.SetValue(str(settings.console_port))
        
        console_ports_grid.Add(self.console_send_port_control, 0, wx.ALL | wx.EXPAND, -1)
        self.console_rcv_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.console_rcv_port_control.SetMaxLength(5)
        self.console_rcv_port_control.SetValue(str(settings.receive_port))
        console_ports_grid.Add(self.console_rcv_port_control, 0, wx.ALL | wx.EXPAND, -1)
        panel_sizer.Add(console_ports_grid, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(0, 25)

        # Match mode radio buttons
        match_mode_text = wx.StaticText(self, label="Matching Mode", style=wx.ALIGN_CENTER)
        match_mode_text.SetFont(header_font)
        panel_sizer.Add(match_mode_text, 0, wx.ALL | wx.EXPAND, 5)
        match_mode_radio_grid = wx.GridSizer(1,2,0,0)
        self.mode_match_all_radio = wx.RadioButton(self, label="Number & Name", style=wx.RB_GROUP)
        match_mode_radio_grid.Add(self.mode_match_all_radio, 0, wx.ALL | wx.EXPAND, 5)
        self.mode_match_all_radio.SetValue(not settings.name_only_match)
        self.mode_match_name_radio = wx.RadioButton(self, label="Name Only")
        match_mode_radio_grid.Add(self.mode_match_name_radio, 0, wx.ALL | wx.EXPAND, 5)
        self.mode_match_name_radio.SetValue(settings.name_only_match)
        panel_sizer.Add(match_mode_radio_grid, 0, wx.ALL | wx.EXPAND, 5)

        # Console type radio box
        console_types = list(CONSOLES)
        self.console_type_radio_box = wx.RadioBox(self, label="Console Type", choices=console_types)
        self.console_type_radio_box.SetSelection(console_types.index(settings.console_type))
        panel_sizer.Add(self.console_type_radio_box, 0, wx.ALL | wx.EXPAND, 5)

        # Daw type radio box
        daw_types = [daw.type for daw in Daw.__subclasses__()]
        self.daw_type_radio_box = wx.RadioBox(self, label="DAW Type", choices=daw_types)
        self.daw_type_radio_box.SetSelection(daw_types.index(settings.daw_type))
        panel_sizer.Add(self.daw_type_radio_box, 0, wx.ALL | wx.EXPAND, 5)

        # OSC Repeater Label
        osc_repeater_text = wx.StaticText(self, label="OSC Repeater", style=wx.ALIGN_CENTER)
        osc_repeater_text.SetFont(header_font)
        panel_sizer.Add(osc_repeater_text, 0, wx.ALL | wx.EXPAND, 5)
        repeater_radio_grid = wx.GridSizer(1, 2, 0, 0)
        self.repeater_radio_enabled = wx.RadioButton(self, label="Repeater Enabled", style=wx.RB_GROUP)
        repeater_radio_grid.Add(self.repeater_radio_enabled, 0, wx.ALL | wx.EXPAND, 5)
        self.repeater_radio_enabled.SetValue(settings.forwarder_enabled)
        self.repeater_radio_disabled = wx.RadioButton(self, label="Repeater Disabled")
        repeater_radio_grid.Add(self.repeater_radio_disabled, 0, wx.ALL | wx.EXPAND, 5)
        self.repeater_radio_disabled.SetValue(not settings.forwarder_enabled)
        panel_sizer.Add(repeater_radio_grid, 0, wx.ALL | wx.EXPAND, 5)
        panel_sizer.Add(0, 10)
        # Console IP Label
        repeater_ip_text = wx.StaticText(self, label="Repeat to IP", style=wx.ALIGN_CENTER)
        repeater_ip_text.SetFont(header_font)
        panel_sizer.Add(repeater_ip_text, 0, wx.ALL | wx.EXPAND, 5)
        # Repeater to  IP Input
        self.repeater_ip_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.repeater_ip_control.SetMaxLength(15)
        self.repeater_ip_control.SetValue(settings.repeater_ip)
        panel_sizer.Add(self.repeater_ip_control, 0, wx.ALL | wx.EXPAND, 5)
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

        # Update console supported features with the currently set console
        self.update_console_supported_features(console)

        # Prefs Window Bindings
        self.Bind(wx.EVT_BUTTON, self.update_button_pressed, update_button)
        self.console_ip_control.Bind(wx.EVT_TEXT, self.changed_console_ip)
        self.console_ip_control.Bind(wx.EVT_KILL_FOCUS, self.check_console_ip)
        self.console_type_radio_box.Bind(wx.EVT_RADIOBOX, self.changed_console_type)
        self.Show()

    def changed_console_type(self, event: wx.CommandEvent) -> None:
        console: Console = CONSOLES[event.GetString()]
        self.update_console_supported_features(console)
        
    def update_console_supported_features(self, console: Console)-> None:
        self.console_rcv_port_control.Enabled = Feature.SEPERATE_RECEIVE_PORT in console.supported_features
        self.mode_match_all_radio.Enabled = Feature.CUE_NUMBER in console.supported_features
        self.mode_match_name_radio.Enabled = Feature.CUE_NUMBER in console.supported_features
        self.repeater_radio_enabled.Enabled = Feature.REPEATER in console.supported_features
        self.repeater_radio_disabled.Enabled = Feature.REPEATER in console.supported_features
        self.repeater_ip_control.Enabled = Feature.REPEATER in console.supported_features
        self.repeater_send_port_control.Enabled = Feature.REPEATER in console.supported_features
        self.repeater_rcv_port_control.Enabled = Feature.REPEATER in console.supported_features
        if Feature.REPEATER not in console.supported_features:
            self.repeater_radio_disabled.SetValue(True)
        if Feature.CUE_NUMBER not in console.supported_features:
            self.mode_match_all_radio.SetValue(True)

    def update_button_pressed(self, e):
        logger.info("Updating configuration settings.")
        # Writing the new values from the preferences panel to settings
        try:
            settings.console_ip = self.console_ip_control.GetValue()
            settings.console_port = str(self.console_send_port_control.GetValue())
            settings.receive_port = str(self.console_rcv_port_control.GetValue())
            settings.repeater_ip = self.repeater_ip_control.GetValue()
            settings.repeater_port = str(self.repeater_send_port_control.GetValue())
            settings.repeater_receive_port = str(self.repeater_rcv_port_control.GetValue())
            settings.name_only_match = self.mode_match_name_radio.GetValue()
            settings.forwarder_enabled = self.repeater_radio_enabled.GetValue()
            settings.console_type = self.console_type_radio_box.GetString(self.console_type_radio_box.GetSelection())
            settings.daw_type = self.daw_type_radio_box.GetString(self.daw_type_radio_box.GetSelection())
            # Force a close/reconnect of the OSC servers by pushing the configuration update.
            MainWindow.BridgeFunctions.update_configuration(con_ip=settings.console_ip,
                                                            rptr_ip=settings.repeater_ip, con_send=settings.console_port,
                                                            con_rcv=settings.receive_port,
                                                            fwd_enable=settings.forwarder_enabled,
                                                            rpr_send=settings.reaper_port,
                                                            rpr_rcv=settings.reaper_receive_port,
                                                            rptr_snd=settings.repeater_port,
                                                            rptr_rcv=settings.repeater_receive_port,
                                                            name_only=settings.name_only_match,
                                                            console_type=settings.console_type,
                                                            daw_type=settings.daw_type)
            # Close the preferences window when update is pressed.
            self.Parent.Destroy()
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")

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
                logger.warning(f"Invalid IP address entered: {ip}")
                # If the input is not a valid IP address, catch the exception and show a dialog
                dlg = wx.MessageDialog(self, "This is not a valid IP address for the console. Please try again",
                                       "Digico-Reaper Link", wx.OK)
                dlg.ShowModal()  # Shows it
                dlg.Destroy()  # Destroy pop-up when finished.
                # Put the focus back on the bad field
                wx.CallAfter(self.console_ip_control.SetFocus)


if __name__ == "__main__":
    try:
        logger.info("Starting Digico-Reaper Link Application")
        app = wx.App(False)
        frame = MainWindow()
        app.MainLoop()
    except Exception as e:
        logger.critical(f"Fatal Error: {e}", exc_info=True)
