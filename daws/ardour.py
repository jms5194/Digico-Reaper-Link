from . import Daw, configure_ardour
from pubsub import pub
from logger_config import logger
from pythonosc import dispatcher, osc_server, udp_client
from typing import Any, Callable
import threading
import time
from constants import PlaybackState, TransportAction


class Ardour(Daw):
    type = "Ardour"
    _shutdown_server_event = threading.Event()

    def __init__(self):
        super().__init__()
        self.ardour_send_lock = threading.Lock()
        self.name_to_match = ""
        self.is_playing = False
        self.is_recording = False
        self.ardour_osc_server = None
        pub.subscribe(self._place_marker_with_name, "place_marker_with_name")
        pub.subscribe(self._incoming_transport_action, "incoming_transport_action")
        pub.subscribe(self._handle_cue_load, "handle_cue_load")
        pub.subscribe(self._shutdown_servers, "shutdown_servers")
        pub.subscribe(self._shutdown_server_event.set, "shutdown_servers")

    def start_managed_threads(
            self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        self._shutdown_server_event.clear()
        logger.info("Starting Ardour Connection thread")
        #start_managed_thread("validate_ardour_prefs_thread", self._validate_ardour_prefs)
        start_managed_thread(
            "daw_connection_thread", self._build_ardour_osc_servers
        )

    def _validate_ardour_prefs(self):
        # If the Ardour config file does not contain an entry for Digico-Reaper Link, add one.
        while not self._shutdown_server_event.is_set():
            try:
                if not self._check_ardour_prefs(3820, 3819):
                    self._add_ardour_prefs(3820, 3819)
                    if configure_ardour.osc_interface_exists(configure_ardour.get_resource_path(True), 3820, 3819):
                        pub.sendMessage("reset_daw", resetdaw=True, dawname="Ardour")
                return True
            except RuntimeError:
                # If Ardour is not running, wait and try again
                logger.error("Ardour not running. Will retry in 1 seconds.")
                time.sleep(1)

    @staticmethod
    def _check_ardour_prefs(rpr_rcv, rpr_send):
        if configure_ardour.osc_interface_exists(configure_ardour.get_resource_path(True), rpr_rcv, rpr_send):
            logger.info("Ardour OSC interface config already exists")
            return True
        else:
            logger.info("Ardour OSC interface config does not exist")
            return False

    @staticmethod
    def _add_ardour_prefs(rpr_rcv, rpr_send):
        configure_ardour.add_OSC_interface(configure_ardour.get_resource_path(True), rpr_rcv, rpr_send)
        logger.info("Added OSC interface to Ardour preferences")

    def _receive_ardour_OSC(self):
        # Receives and distributes OSC from Ardour, based on matching OSC values
        self.ardour_dispatcher.map("/transport_play", self._current_transport_state)
        self.ardour_dispatcher.map("/transport_stop", self._current_transport_state)
        self.ardour_dispatcher.map("/rec_enable_toggle", self._current_transport_state)

    def _build_ardour_osc_servers(self):
        # Connect to Ardour via OSC
        if self._validate_ardour_prefs():
            logger.info("Starting Ardour OSC server")
            self.ardour_client = udp_client.SimpleUDPClient("127.0.0.1", 3819)
            self.ardour_dispatcher = dispatcher.Dispatcher()
            self._receive_ardour_OSC()
            try:
                self.ardour_osc_server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 3820),
                                                                        self.ardour_dispatcher)
                logger.info("Ardour OSC server started")
                self.ardour_osc_server.serve_forever()
            except Exception as e:
                logger.error(f"Ardour OSC server startup error: {e}")

    def _current_transport_state(self, osc_address, val):
        # Watches what the Ardour playhead is doing.
        playing = None
        recording = None
        if osc_address == "/transport_play":
            if val == 0:
                playing = False
            elif val == 1:
                playing = True
        elif osc_address == "/rec_enable_toggle":
            if val == 0:
                recording = False
            elif val == 1:
                recording = True
        if playing is True:
            self.is_playing = True
            logger.info("Ardour is playing")
        elif playing is False:
            self.is_playing = False
            logger.info("Ardour is not playing")
        if recording is True:
            self.is_recording = True
            logger.info("Ardour is recording")
        elif recording is False:
            self.is_recording = False
            logger.info("Ardour is not recording")

    def _goto_marker_by_name(self, marker_name):
        with self.ardour_send_lock:
            self.ardour_client.send_message("/marker", marker_name)

    def _place_marker_with_name(self, marker_name):
        print(f"Placing marker with name: {marker_name}")
        with self.ardour_send_lock:
            self.ardour_client.send_message("/marker/get", None)
            self.ardour_client.send_message("/add_marker", marker_name)

    def _incoming_transport_action(self, transport_action):
        try:
            if transport_action is TransportAction.PLAY:
                self._ardour_play()
            elif transport_action is TransportAction.STOP:
                self._ardour_stop()
            elif transport_action is TransportAction.RECORD:
                self._ardour_rec()
        except Exception as e:
            logger.error(f"Error processing transport macros: {e}")

    def _ardour_play(self):
        with self.ardour_send_lock:
            self.ardour_client.send_message("/transport_play", 1.0)

    def _ardour_stop(self):
        with self.ardour_send_lock:
            self.ardour_client.send_message("/transport_stop", 1.0)

    def _ardour_rec(self):
        # Sends action to skip to end of project and then record, to prevent overwrites
        from app_settings import settings
        settings.marker_mode = "Recording"
        pub.sendMessage("mode_select_osc", selected_mode=PlaybackState.RECORDING)
        with self.ardour_send_lock:
            self.ardour_client.send_message("/goto_end", None)
            self.ardour_client.send_message("/rec_enable_toggle", 1.0)
            self.ardour_client.send_message("/transport_play", 1.0)

    def _handle_cue_load(self, cue: str) -> None:
        from app_settings import settings
        if settings.marker_mode == "Recording" and self.is_recording is True and self.is_playing is True:
            self._place_marker_with_name(cue)
        elif settings.marker_mode == "PlaybackTrack" and self.is_playing is False:
            self._goto_marker_by_name(cue)
            # TODO: Add name only logic here

    def _shutdown_servers(self):
        try:
            if self.ardour_osc_server:
                self.ardour_osc_server.shutdown()
                self.ardour_osc_server.server_close()
            logger.info("Ardour OSC Server shutdown completed")
        except Exception as e:
            logger.error(f"Error shutting down Ardour server: {e}")