import ipaddress
import platform
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
        MainPanel(self)
        # Build a menubar:

        menu_bar = wx.MenuBar()
        if platform.system() == 'Darwin':
            main_menu = menu_bar.OSXGetAppleMenu()
            self.Bind(wx.EVT_MENU, self.on_close, main_menu.FindItemById(wx.ID_EXIT))
        else:
            main_menu = wx.Menu()
        
        properties_menuitem = main_menu.Prepend(wx.ID_PROPERTIES, "Properties\tCTRL+,")
        main_menu.PrependSeparator()
        about_menuitem = main_menu.Prepend(wx.ID_ABOUT)
        main_menu.InsertSeparator(1)
        if platform.system() != 'Darwin':
            m_exit = main_menu.Append(wx.ID_EXIT, "&Exit\tCTRL+Q")
            menu_bar.Append(main_menu, "&File")
            self.Bind(wx.EVT_MENU, self.on_close, m_exit)
        self.SetMenuBar(menu_bar)

        # Main Window Bindings
        self.Bind(wx.EVT_MENU, self.on_about, about_menuitem)
        self.Bind(wx.EVT_MENU, self.launch_prefs, properties_menuitem)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        pub.subscribe(self.update_display_settings, "update_main_window_display_settings")
        self.update_display_settings()

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

    def update_display_settings(self) -> None:
        if settings.always_on_top:
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE| wx.STAY_ON_TOP)
        else: 
            self.SetWindowStyle(wx.DEFAULT_FRAME_STYLE)


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
        pub.subscribe(self.call_for_daw_reset, "reset_daw")
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

    def call_for_daw_reset(self, resetdaw, dawname):
        logger.info(f"{dawname} has been auto configured. Requesting restart")
        dlg = wx.MessageDialog(self,
                               f"{dawname} has been configured for use with Digico-Reaper Link. "
                               f"Please restart {dawname} and press OK",
                               f"{dawname} Configured", wx.OK | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def attemptreconnect(e):
        logger.info("Manual reconnection requested.")
        # Just forces a close/reconnect of the OSC servers by manually updating the configuration.
        MainWindow.BridgeFunctions.update_configuration(
            con_ip=settings.console_ip,
            rptr_ip=settings.repeater_ip,
            con_send=settings.console_port,
            con_rcv=settings.receive_port,
            fwd_enable=settings.forwarder_enabled,
            rpr_send=settings.reaper_port,
            rpr_rcv=settings.reaper_receive_port,
            rptr_snd=settings.repeater_port,
            rptr_rcv=settings.repeater_receive_port,
            name_only=settings.name_only_match,
            console_type=settings.console_type,
            daw_type=settings.daw_type,
            always_on_top=settings.always_on_top,
        )


class PrefsWindow(wx.Frame):
    # This is our preferences window pane
    def __init__(self, title, parent, console: Console):
        logger.info("Creating PrefsWindow")
        wx.Frame.__init__(self, parent=parent, title=title, style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        PrefsPanel(self, console=console)
        self.Fit()
        if self.GetSize().Width < 300:
            self.SetSize(width=300,height=-1)
        self.Show()

INTERNAL_PORT_SPACING=5
INTERNAL_SPACING=10
EXTERNAL_SPACING=15

LABEL_ROW = 1

class PrefsPanel(wx.Panel):
    def __init__(self, parent, console: Console):
        logger.info("Creating PrefsPanel")
        wx.Panel.__init__(self, parent)
        # Define Fonts:
        self.ip_inspected = False
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        header_font = wx.Font().Bold()
        header_font.MakeLarger()
        header_font.MakeLarger()

        item_font = wx.Font()
        item_font.SetWeight(wx.FONTWEIGHT_MEDIUM)
        item_font.MakeLarger()

        port_font = wx.Font()
        port_font.SetWeight(wx.FONTWEIGHT_LIGHT)
        port_font.MakeSmaller()

        # Console Section
        panel_sizer.AddSpacer(EXTERNAL_SPACING)
        console_header = wx.StaticText(self, label="Console", style=wx.ALIGN_CENTER)
        console_header.SetFont(header_font)
        panel_sizer.Add(console_header, flag=wx.LEFT | wx.RIGHT | wx.EXPAND, border=EXTERNAL_SPACING)
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        panel_sizer.Add(wx.StaticLine(self), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=EXTERNAL_SPACING)
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        console_main_section = wx.FlexGridSizer(2, INTERNAL_SPACING, INTERNAL_SPACING)
        console_main_section.AddGrowableCol(1)
        console_main_section.SetFlexibleDirection(direction=wx.HORIZONTAL)
        # Console Type
        console_main_section.Add(wx.StaticText(self, label="Type:", style=wx.ALIGN_RIGHT))
        console_types = list(CONSOLES)
        console_types.sort()
        self.console_type_choice = wx.Choice(self, choices=console_types)
        self.console_type_choice.SetSelection(console_types.index(settings.console_type))
        console_main_section.Add(self.console_type_choice, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        # Console IP
        console_ip_label = wx.StaticText(self, label="IP address:", style=wx.ALIGN_RIGHT)
        console_main_section.Add(console_ip_label)
        self.console_ip_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.console_ip_control.SetMaxLength(15)
        self.console_ip_control.SetValue(settings.console_ip)
        console_main_section.Add(self.console_ip_control, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        # label_min_width is used to force FlexSizers with only a checkbox (so no label) to look right
        label_min_width = console_ip_label.GetBestSize().width
        # Console Ports
        console_main_section.AddStretchSpacer()
        console_main_ports_label_section = wx.GridSizer(1,2,0,INTERNAL_SPACING)
        console_main_send_label = wx.StaticText(self, label="Send")
        console_main_send_label.SetFont(port_font)
        console_main_ports_label_section.Add(console_main_send_label, flag=wx.ALIGN_BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        console_main_receive_label = wx.StaticText(self, label="Receive")
        console_main_receive_label.SetFont(port_font)
        console_main_ports_label_section.Add(console_main_receive_label, flag=wx.ALIGN_BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        console_main_section.Add(console_main_ports_label_section, flag=wx.EXPAND, userData=LABEL_ROW)
        console_main_section.Add(wx.StaticText(self, label="Ports:", style=wx.ALIGN_RIGHT))
        console_main_ports_section = wx.GridSizer(1,2,0,INTERNAL_SPACING)
        self.console_send_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.console_send_port_control.SetMaxLength(5)
        self.console_send_port_control.SetValue(str(settings.console_port))
        console_main_ports_section.Add(self.console_send_port_control, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        self.console_rcv_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.console_rcv_port_control.SetMaxLength(5)
        self.console_rcv_port_control.SetValue(str(settings.receive_port))
        console_main_ports_section.Add(self.console_rcv_port_control, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        console_main_section.Add(console_main_ports_section, flag=wx.EXPAND)
        panel_sizer.Add(console_main_section, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=EXTERNAL_SPACING)

        # Console Repeater Section
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        panel_sizer.Add(wx.StaticLine(self), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=EXTERNAL_SPACING)
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        console_repeater_section = wx.FlexGridSizer(2, INTERNAL_SPACING, INTERNAL_SPACING)
        console_repeater_section.AddGrowableCol(1)
        console_repeater_section.SetFlexibleDirection(direction=wx.HORIZONTAL)
        console_repeater_section.AddStretchSpacer()
        # Repeater Enabled
        self.repeater_radio_enabled = wx.CheckBox(self, label="Repeater enabled")
        self.repeater_radio_enabled.SetValue(settings.forwarder_enabled)
        console_repeater_section.Add(self.repeater_radio_enabled, flag=wx.EXPAND)
        # Repeater IP
        console_repeater_section.Add(wx.StaticText(self, label="Tablet IP:", style=wx.ALIGN_RIGHT))
        self.repeater_ip_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.repeater_ip_control.SetMaxLength(15)
        self.repeater_ip_control.SetValue(settings.repeater_ip)
        console_repeater_section.Add(self.repeater_ip_control, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        # Repeater Ports
        console_repeater_section.AddStretchSpacer()
        console_repeater_ports_label_section = wx.GridSizer(1,2,0,INTERNAL_SPACING)
        console_send_label = wx.StaticText(self, label="Send")
        console_send_label.SetFont(port_font)
        console_repeater_ports_label_section.Add(console_send_label, flag=wx.ALIGN_BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        console_receive_label = wx.StaticText(self, label="Receive")
        console_receive_label.SetFont(port_font)
        console_repeater_ports_label_section.Add(console_receive_label, flag=wx.ALIGN_BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        console_repeater_section.Add(console_repeater_ports_label_section, flag=wx.EXPAND, userData=LABEL_ROW)
        console_repeater_section.Add(wx.StaticText(self, label="Ports:", style=wx.ALIGN_RIGHT))
        console_repeater_ports_section = wx.GridSizer(1,2,0,INTERNAL_SPACING)
        self.repeater_send_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.repeater_send_port_control.SetMaxLength(5)
        self.repeater_send_port_control.SetValue(str(settings.repeater_port))
        console_repeater_ports_section.Add(self.repeater_send_port_control, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        self.repeater_rcv_port_control = wx.TextCtrl(self, style=wx.TE_CENTER)
        self.repeater_rcv_port_control.SetMaxLength(5)
        self.repeater_rcv_port_control.SetValue(str(settings.repeater_receive_port))
        console_repeater_ports_section.Add(self.repeater_rcv_port_control, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        console_repeater_section.Add(console_repeater_ports_section, flag=wx.EXPAND)
        panel_sizer.Add(console_repeater_section, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=EXTERNAL_SPACING)

        # DAW Section
        daw_header = wx.StaticText(self, label="DAW", style=wx.ALIGN_CENTER)
        daw_header.SetFont(header_font)
        panel_sizer.Add(daw_header, flag=wx.LEFT | wx.RIGHT | wx.EXPAND, border=EXTERNAL_SPACING)
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        panel_sizer.Add(wx.StaticLine(self), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=EXTERNAL_SPACING)
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        daw_section = wx.FlexGridSizer(2,INTERNAL_SPACING, INTERNAL_SPACING)
        daw_section.AddGrowableCol(1)
        daw_section.SetFlexibleDirection(direction=wx.HORIZONTAL)
        daw_section.Add(wx.StaticText(self, label="Type:", style=wx.ALIGN_RIGHT))        
        # DAW Type
        daw_types = [daw.type for daw in Daw.__subclasses__()]
        daw_types.sort()
        self.daw_type_choice = wx.Choice(self, choices=daw_types)
        self.daw_type_choice.SetSelection(daw_types.index(settings.daw_type))
        daw_section.Add(self.daw_type_choice, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        panel_sizer.Add(daw_section, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=EXTERNAL_SPACING)

        # Application Settings Section
        application_header = wx.StaticText(self, label="Application", style=wx.ALIGN_CENTER)
        application_header.SetFont(header_font)
        panel_sizer.Add(application_header, flag=wx.LEFT | wx.RIGHT | wx.EXPAND, border=EXTERNAL_SPACING)
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        panel_sizer.Add(wx.StaticLine(self), flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=EXTERNAL_SPACING)
        panel_sizer.AddSpacer(INTERNAL_SPACING)
        app_settings_section = wx.FlexGridSizer(2, INTERNAL_SPACING, INTERNAL_SPACING)
        app_settings_section.AddGrowableCol(1)
        app_settings_section.SetFlexibleDirection(direction=wx.VERTICAL)
        # Always On Top
        app_settings_section.Add(width=label_min_width,height=0)
        self.always_on_top_checkbox = wx.CheckBox(self, label="Always display on top")
        self.always_on_top_checkbox.SetValue(settings.always_on_top)
        app_settings_section.Add(self.always_on_top_checkbox, flag=wx.EXPAND)
        # Only match cue name
        app_settings_section.AddStretchSpacer()
        self.match_mode_label_only = wx.CheckBox(self,label="Only match cue name")
        app_settings_section.Add(self.match_mode_label_only, flag=wx.EXPAND)
        self.match_mode_label_only.SetValue(settings.name_only_match)
        panel_sizer.Add(app_settings_section, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=EXTERNAL_SPACING)
        
        for child in panel_sizer.GetChildren():
            if isinstance(child, wx.SizerItem) and child.IsSizer():
                child_sizer = child.GetSizer()
                if isinstance(child_sizer, wx.FlexGridSizer):
                    child_sizer.SetFlexibleDirection(wx.BOTH)
                    child_sizer.Layout()
                    for flex_child in child_sizer.GetChildren():
                        if isinstance(flex_child, wx.SizerItem) and not flex_child.IsSpacer():
                            flex_child_user_data = flex_child.GetUserData()
                            if flex_child_user_data != LABEL_ROW:
                                flex_child.SetMinSize(wx.Size(label_min_width,-1))
        # Update Button
        update_button = wx.Button(self, -1, "Update")
        panel_sizer.Add(update_button, 0, wx.ALL | wx.EXPAND, EXTERNAL_SPACING)
        self.SetSizer(panel_sizer)
        self.Fit()

        # Update console supported features with the currently set console
        self.update_console_supported_features(console)

        # Prefs Window Bindings
        self.Bind(wx.EVT_BUTTON, self.update_button_pressed, update_button)
        self.console_ip_control.Bind(wx.EVT_TEXT, self.changed_console_ip)
        self.console_ip_control.Bind(wx.EVT_KILL_FOCUS, self.check_console_ip)
        self.console_type_choice.Bind(wx.EVT_CHOICE, self.changed_console_type)
        self.Show()

    def changed_console_type(self, event: wx.CommandEvent) -> None:
        console: Console = CONSOLES[event.GetString()]
        self.update_console_supported_features(console)
        
    def update_console_supported_features(self, console: Console)-> None:
        self.console_rcv_port_control.Enabled = Feature.SEPERATE_RECEIVE_PORT in console.supported_features
        self.match_mode_label_only.Enabled = Feature.CUE_NUMBER in console.supported_features
        self.repeater_radio_enabled.Enabled = Feature.REPEATER in console.supported_features
        self.repeater_ip_control.Enabled = Feature.REPEATER in console.supported_features
        self.repeater_send_port_control.Enabled = Feature.REPEATER in console.supported_features
        self.repeater_rcv_port_control.Enabled = Feature.REPEATER in console.supported_features
        if Feature.REPEATER not in console.supported_features:
            self.repeater_radio_enabled.SetValue(False)
        if Feature.CUE_NUMBER not in console.supported_features:
            self.match_mode_label_only.SetValue(False)

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
            settings.name_only_match = self.match_mode_label_only.GetValue()
            settings.forwarder_enabled = self.repeater_radio_enabled.GetValue()
            settings.console_type = self.console_type_choice.GetString(self.console_type_choice.GetSelection())
            settings.daw_type = self.daw_type_choice.GetString(self.daw_type_choice.GetSelection())
            settings.always_on_top = self.always_on_top_checkbox.GetValue()
            # Force a close/reconnect of the OSC servers by pushing the configuration update.
            MainWindow.BridgeFunctions.update_configuration(
                con_ip=settings.console_ip,
                rptr_ip=settings.repeater_ip,
                con_send=settings.console_port,
                con_rcv=settings.receive_port,
                fwd_enable=settings.forwarder_enabled,
                rpr_send=settings.reaper_port,
                rpr_rcv=settings.reaper_receive_port,
                rptr_snd=settings.repeater_port,
                rptr_rcv=settings.repeater_receive_port,
                name_only=settings.name_only_match,
                console_type=settings.console_type,
                daw_type=settings.daw_type,
                always_on_top=settings.always_on_top,
            )
            # Close the preferences window when update is pressed.
            self.Parent.Destroy()
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
        pub.sendMessage("update_main_window_display_settings")

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
