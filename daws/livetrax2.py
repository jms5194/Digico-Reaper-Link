from . import Daw
from pubsub import pub
from logger_config import logger
from pythonosc import dispatcher, osc_server, udp_client
from typing import Any, Callable
import threading

class LiveTrax2(Daw):
    type = "LiveTrax2"

    def __init__(self):
        super().__init__()
        self.lt2_send_lock = threading.Lock()
        self.name_to_match = ""
        self.is_playing = False
        self.is_recording = False
        self.lt2_osc_server = None
        pub.subscribe(self._place_marker_with_name, "place_marker_with_name")
        pub.subscribe(self._incoming_transport_action, "incoming_transport_action")
        pub.subscribe(self._handle_cue_load, "handle_cue_load")
        pub.subscribe(self._shutdown_servers, "shutdown_servers")

    def start_managed_threads(
            self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        logger.info("Starting LiveTrax2 Connection thread")
        start_managed_thread(
            "daw_connection_thread", self._build_lt2_osc_servers
        )

    def _receive_lt2_OSC(self):
        # Receives and distributes OSC from LiveTrax2, based on matching OSC values
        self.lt2_dispatcher.map("/transport_play", self._current_transport_state)
        self.lt2_dispatcher.map("/transport_stop", self._current_transport_state)
        self.lt2_dispatcher.map("/rec_enable_toggle", self._current_transport_state)

    def _build_lt2_osc_servers(self):
        # Connect to LiveTrax2 via OSC
        logger.info("Starting LiveTrax2 OSC server")
        self.lt2_client = udp_client.SimpleUDPClient("127.0.0.1", 3819)
        self.lt2_dispatcher = dispatcher.Dispatcher()
        self._receive_lt2_OSC()
        try:
            self.lt2_osc_server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", 3820),
                                                                      self.lt2_dispatcher)
            logger.info("LiveTrax2 OSC server started")
            self.lt2_osc_server.serve_forever()
        except Exception as e:
            logger.error(f"LiveTrax2 OSC server startup error: {e}")

    def _marker_matcher(self, osc_address, test_name):
        # Matches a marker composite name with its Reaper ID
        from app_settings import settings
        address_split = osc_address.split("/")
        marker_id = address_split[2]
        if settings.name_only_match:
            test_name = test_name.split(" ")
            test_name = test_name[1:]
            test_name = " ".join(test_name)
        if test_name == self.name_to_match:
            self._goto_marker_by_name(marker_id)

    def _current_transport_state(self, osc_address, val):
        # Watches what the LiveTrax2 playhead is doing.
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
            logger.info("LiveTrax2 is playing")
        elif playing is False:
            self.is_playing = False
            logger.info("LiveTrax2 is not playing")
        if recording and playing is True:
            self.is_recording = True
            logger.info("LiveTrax2 is recording")
        elif recording is False:
            self.is_recording = False
            logger.info("LiveTrax2 is not recording")

    def _goto_marker_by_name(self, marker_name):
        with self.lt2_send_lock:
            self.lt2_client.send_message("/marker", marker_name)

    def _place_marker_with_name(self, marker_name):
        with self.lt2_send_lock:
            self.lt2_client.send_message("/refresh", None)
            self.lt2_client.send_message("/add_marker", marker_name)

    def _incoming_transport_action(self, transport_action):
        try:
            if transport_action == "play":
                self._lt2_play()
            elif transport_action == "stop":
                self._lt2_stop()
            elif transport_action == "rec":
                self._lt2_rec()
        except Exception as e:
            logger.error(f"Error processing transport macros: {e}")

    def _lt2_play(self):
        with self.lt2_send_lock:
            self.lt2_client.send_message("/transport_play", 1.0)

    def _lt2_stop(self):
        with self.lt2_send_lock:
            self.lt2_client.send_message("/transport_stop", 1.0)

    def _lt2_rec(self):
        # Sends action to skip to end of project and then record, to prevent overwrites
        from app_settings import settings
        settings.marker_mode = "Recording"
        pub.sendMessage("mode_select_osc", selected_mode="Recording")
        with self.lt2_send_lock:
            self.lt2_client.send_message("/goto_end", None)
            self.lt2_client.send_message("/rec_enable_toggle", 1.0)
            self.lt2_client.send_message("/transport_play", 1.0)

    def _handle_cue_load(self, cue: str) -> None:
        from app_settings import settings
        if settings.marker_mode == "Recording" and self.is_recording is True:
            self._place_marker_with_name(cue)
        elif settings.marker_mode == "PlaybackTrack" and self.is_playing is False:
            self._goto_marker_by_name(cue)

    def _shutdown_servers(self):
        try:
            if self.lt2_osc_server:
                self.lt2_osc_server.shutdown()
                self.lt2_osc_server.server_close()
            logger.info(f"LiveTrax2 OSC Server shutdown completed")
        except Exception as e:
            logger.error(f"Error shutting down LiveTrax2 server: {e}")