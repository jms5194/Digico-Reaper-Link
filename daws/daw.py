from typing import Callable
import threading
from pubsub import pub

class Daw:
    type = "Unknown"
    _shutdown_server_event: threading.Event

    def __init__(self) -> None:
        self._shutdown_server_event = threading.Event()
        pub.subscribe(self._shutdown_server_event.set, "shutdown_servers")

    def start_managed_threads(
        self, start_managed_thread: Callable[[str, Callable], None]
    ) -> None:
        pass

