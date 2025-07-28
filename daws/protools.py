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


    def do_newmemloc(self, args):
        'Create a new marker memory location: NEWMEMLOC start-time'
        command_args = {'name': 'New Marker',
                        'start_time': args.strip(),
                        'end_time': args.strip(),
                        'time_properties': 'TP_Marker',
                        'reference': 'MLR_FollowTrackTimebase',
                        'general_properties': {
                            'zoom_settings': False,
                            'pre_post_roll_times': False,
                            'track_visibility': False,
                            'track_heights': False,
                            'group_enables': False,
                            'window_configuration': False,
                        },
                        'comments': "Created by toolshell",
                        'color_index': 1,
                        'location': 'MLC_MainRuler'
                        }

        self.run_command_on_session(pt.CreateMemoryLocation, command_args)

    def _place_marker_with_name(self, marker_name):
        #assert self.pt_engine_connection
        #for i in self.pt_engine_connection.get_memory_locations():
        #    print(i)

        #self.pt_engine_connection.create_memory_location(memory_number=10, name=marker_name, )
        pass


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
        pass


    def _pro_tools_play(self):
        assert self.pt_engine_connection
        current_transport_state = self.pt_engine_connection.transport_state()
        if current_transport_state not in ("TS_TransportPlaying", "TS_TransportRecording"):
            try:
                self.pt_engine_connection.toggle_play_state()
            except ptsl.errors.CommandError as e:
                if e.error_type == pt.PT_NoOpenedSession:
                    logger.error("Play command failed, no session is currently open")
                    return False

    def _pro_tools_stop(self):
        assert self.pt_engine_connection
        current_transport_state = self.pt_engine_connection.transport_state()
        if current_transport_state not in ("TS_TransportStopped", "TS_TransportStopping"):
            try:
                self.pt_engine_connection.toggle_play_state()
            except ptsl.errors.CommandError as e:
                if e.error_type == pt.PT_NoOpenedSession:
                    logger.error("Play command failed, no session is currently open")
                    return False

    def _pro_tools_rec(self):
        assert self.pt_engine_connection
        current_transport_state = self.pt_engine_connection.transport_state()
        current_armed_state = self.pt_engine_connection.transport_armed()
        if not current_armed_state:
            self.pt_engine_connection.toggle_record_enable()
            if current_transport_state is not "TS_TransportRecording":
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