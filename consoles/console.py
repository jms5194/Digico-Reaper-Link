import threading
from enum import Enum
from typing import Callable, List, Optional

from pubsub import pub


class Feature(Enum):
    CUE_NUMBER = 1
    REPEATER = 2
    SEPERATE_RECEIVE_PORT = 3


class Console:
    fixed_port: Optional[int] = None
    _shutdown_server_event: threading.Event
    supported_features: List[Feature]
    type = "Unknown"

    def __init__(self) -> None:
        self._shutdown_server_event = threading.Event()
        pub.subscribe(self._shutdown_server_event.set, "shutdown_servers")

    def heartbeat(self) -> None:
        pass

    def start_managed_threads(
        self, start_managed_thread: Callable[[str, Callable], None]
    ) -> None:
        pass
