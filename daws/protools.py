from . import Daw
import ptsl
from ptsl import PTSL_pb2 as pt
from pubsub import pub
from typing import Any, Callable
from logger_config import logger
import threading
import time
import sys

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
            if self.pt_engine_connection.host_ready_check():
                print("connected")

    def _place_marker_with_name(self, marker_name):
        pass

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