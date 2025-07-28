from setuptools.command.build_ext import if_dl

from . import Daw
import ptsl
from ptsl import PTSL_pb2 as pt
from pubsub import pub
from typing import Any, Callable
from logger_config import logger
import threading
import sys
import time
from typing import Optional

class ProTools(Daw):
    type = "ProTools"

    def __init__(self):
        super().__init__()
        self.pt_engine_connection = None
        self.pt_send_lock = threading.Lock()
        pub.subscribe(self._place_marker_with_name, "place_marker_with_name")
        pub.subscribe(self._incoming_transport_action, "incoming_transport_action")
        pub.subscribe(self._handle_cue_load, "handle_cue_load")
        pub.subscribe(self._shutdown_servers, "shutdown_servers")

    def start_managed_threads(
            self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        logger.info("Starting Pro Tools Connection thread")
        start_managed_thread(
            "daw_connection_thread", self._open_protools_connection
        )

    def _open_protools_connection(self):
        self.pt_engine_connection = ptsl.engine.Engine(company_name="JSSD",
                                         application_name=sys.argv[0])
        if self.pt_engine_connection is not None:
            logger.info("Connection established to Pro Tools")

    def _place_marker_with_name(self, marker_name):
        with self.pt_send_lock:
            assert self.pt_engine_connection
            try:
                self.pt_engine_connection.create_memory_location(memory_number=-1, start_time="current_pos", name=marker_name, location="MLC_MainRuler")
                #start_time as current_pos is a hacky way to get it to drop where the playhead is- but throws an error
            except ptsl.errors.CommandError as e:
                if e.error_type == pt.PT_InvalidParameter:
                    logger.error("Bad parameter input to create_memory_location")

    def _incoming_transport_action(self, transport_action):
        try:
            if transport_action == "play":
                self._pro_tools_play()
            elif transport_action == "stop":
                self._pro_tools_stop()
            elif transport_action == "rec":
                self._pro_tools_rec()
        except Exception as e:
            logger.error(f"Error processing transport macros: {e}")

    def _handle_cue_load(self, cue: str):
        from app_settings import settings
        if settings.marker_mode == "Recording" and self._get_current_transport_state() == "TS_TransportRecording":
            self._place_marker_with_name(cue)
        elif settings.marker_mode == "PlaybackTrack" and self._get_current_transport_state() == "TS_TransportStopped":
            self._get_marker_id_by_name(cue)

    def _get_marker_id_by_name(self, name):
        from app_settings import settings
        if self._get_current_transport_state() not in ("TS_TransportPlaying", "TS_TransportRecording"):
            name_to_match = name
        if settings.name_only_match:
            name_to_match = name_to_match.split(" ")
            name_to_match = name_to_match[1:]
            name_to_match = " ".join(name_to_match)
        with self.pt_send_lock:
            mem_locs = self.pt_engine_connection.get_memory_locations()
            for i in mem_locs:
                if name_to_match == i.name:
                    print(i.name)
                    self._goto_marker_by_id(i.memory_number)
                    print("found")

    def _goto_marker_by_id(self, memory_number):
        pass

    def _get_current_transport_state(self):
        with self.pt_send_lock:
            return self.pt_engine_connection.transport_state()

    def _pro_tools_play(self):
        with self.pt_send_lock:
            assert self.pt_engine_connection
            current_transport_state = self.pt_engine_connection.transport_state()
            if current_transport_state not in ("TS_TransportPlaying", "TS_TransportRecording"):
                try:
                    self.pt_engine_connection.toggle_play_state()
                except ptsl.errors.CommandError as e:
                    if e.error_type == pt.PT_NoOpenedSession:
                        logger.error("Play command failed, no session is currently open")
                        return False
            return None

    def _pro_tools_stop(self):
        with self.pt_send_lock:
            assert self.pt_engine_connection
            current_transport_state = self.pt_engine_connection.transport_state()
            if current_transport_state not in ("TS_TransportStopped", "TS_TransportStopping"):
                try:
                    self.pt_engine_connection.toggle_play_state()
                except ptsl.errors.CommandError as e:
                    if e.error_type == pt.PT_NoOpenedSession:
                        logger.error("Play command failed, no session is currently open")
                        return False
            return None

    def _pro_tools_rec(self):
        with self.pt_send_lock:
            assert self.pt_engine_connection
            current_transport_state = self.pt_engine_connection.transport_state()
            current_armed_state = self.pt_engine_connection.transport_armed()
            if not current_armed_state:
                self.pt_engine_connection.toggle_record_enable()
                if current_transport_state != "TS_TransportRecording":
                    try:
                        self.pt_engine_connection.toggle_play_state()
                    except ptsl.errors.CommandError as e:
                        if e.error_type == pt.PT_NoOpenedSession:
                            logger.error("Play command failed, no session is currently open")
                            return False

    def _shutdown_servers(self):
        try:
            if self.pt_engine_connection:
                self.pt_engine_connection.close()
                logger.info("Disconnected from Pro Tools")
        except Exception as e:
            logger.error(f"Error closing Pro Tools connection: {e}")