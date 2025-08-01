from . import Daw
from pubsub import pub
from logger_config import logger
from typing import Any, Callable
import threading

from py4j.java_gateway import JavaGateway

class Bitwig(Daw):
    type = "Bitwig"
    _shutdown_server_event = threading.Event()

    def __init__(self):
        super().__init__()
        self.bitwig_send_lock = threading.Lock()
        pub.subscribe(self._place_marker_with_name, "place_marker_with_name")
        pub.subscribe(self._incoming_transport_action, "incoming_transport_action")
        pub.subscribe(self._handle_cue_load, "handle_cue_load")
        pub.subscribe(self._shutdown_servers, "shutdown_servers")
        pub.subscribe(self._shutdown_server_event.set, "shutdown_servers")

    def start_managed_threads(
            self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        self._shutdown_server_event.clear()
        logger.info("Starting Bitwig Connection thread")
        start_managed_thread(
            "daw_connection_thread", self._build_bitwig_connection
        )


    def _build_bitwig_connection(self):
        gateway = JavaGateway()
        e_p = gateway.entry_point
        host = e_p.getHost()
        println = host.println
        logger.info("Attempting to Connect to Bitwig")
        println("Connected to Bitwig")
        self.bitwig_transport = e_p.getTransport()

    def _incoming_transport_action(self, transport_action):
        try:
            if transport_action == "play":
                self._bitwig_play()
            elif transport_action == "stop":
                self._bitwig_stop()
            elif transport_action == "rec":
                self._bitwig_rec()
        except Exception as e:
            logger.error(f"Error processing transport macros: {e}")

    def _place_marker_with_name(self, marker_name: str):
        self.bitwig_transport.record()
        self.bitwig_transport.play()

    def _handle_cue_load(self):
        pass

    def _bitwig_play(self):
        if not self.bitwig_transport.is_playing():
            self.bitwig_transport.play()

    def _bitwig_stop(self):
        self.bitwig_transport.stop()

    def _bitwig_rec(self):
        if not self.bitwig_transport.is_playing():
            self.bitwig_transport.record()
            self.bitwig_transport.play()
        else:
            self.bitwig_transport.stop()
            self.bitwig_transport.record()
            self.bitwig_transport.play()

    def _shutdown_servers(self):
        pass


