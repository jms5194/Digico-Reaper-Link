from . import Daw
import ptsl
from ptsl import PTSL_pb2 as pt
from pubsub import pub
from typing import Any, Callable
from logger_config import logger
import threading
import time
import sys
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
        self.pt_engine_connection = ptsl.client.Client(company_name="JSSD",
                                         application_name=sys.argv[0])
        if self.pt_engine_connection is not None:
            logger.info("Connection established to Pro Tools")

    def run_command_on_session(self, command_id: pt.CommandId,
                               args: dict) -> Optional[dict]:
        if self.pt_engine_connection is None:
            logger.error("Command failed, not connected to Pro Tools")
            return None

        try:
            r = self.pt_engine_connection.run_command(command_id, args)
            return r
        except ptsl.errors.CommandError as e:
            if e.error_type == pt.PT_NoOpenedSession:
                logger.error("Command failed, no session is currently open in Pro Tools")
                return None
        except Exception:
            logger.error("Command failed, Pro Tools may not be running")
            return None

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
        self.do_newmemloc("00:01:00:00")

    def _incoming_transport_action(self, transport_action):
        pass

    def _handle_cue_load(self, cue: str):
        pass

    def _shutdown_servers(self):
        try:
            if self.pt_engine_connection:
                self.pt_engine_connection.close()
                logger.info("Disconnected from Pro Tools")
        except Exception as e:
            logger.error(f"Error closing Pro Tools connection: {e}")