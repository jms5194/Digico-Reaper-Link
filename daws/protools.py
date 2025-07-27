from . import Daw
from ptsl import open_engine
from pubsub import pub
from typing import Any, Callable
from logger_config import logger
import threading


class ProTools(Daw):
    type = "ProTools"

    def __init__(self):
        super().__init__()
        self.pt_engine_connection = None
        pub.subscribe(self._place_marker_with_name, "place_marker_with_name")
        pub.subscribe(self._incoming_transport_action, "incoming_transport_action")
        pub.subscribe(self.handle_cue_load, "handle_cue_load")
        pub.subscribe(self._shutdown_servers, "shutdown_servers")

    def start_managed_threads(
            self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        logger.info("Starting Pro Tools Connection thread")
        start_managed_thread(
            "daw_connection_thread", self._open_protools_connection
        )

    def _open_protools_connection(self):
        try:
            with open_engine(company_name="JSSD", application_name="CONSOLE_LINK") as self.pt_engine_connection:
                if self.pt_engine_connection.host_ready_check():
                    logger.info("Successfully connected to Pro Tools")
        except Exception as e:
            logger.error(f"Unable to establish connection to Reaper: {e}")

    def _shutdown_servers(self):
        try:
            if self.pt_engine_connection:
                self.pt_engine_connection.close()
                logger.info("Disconnected from Pro Tools")
        except Exception as e:
            logger.error(f"Error closing Pro Tools connection: {e}")