from typing import Callable, List


class Daw:
    type = "Unknown"

    def __init__(self) -> None:
        pass

    def start_managed_threads(
        self, start_managed_thread: Callable[[str, Callable], None]
    ) -> None:
        pass

