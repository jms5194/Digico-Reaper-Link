import socket
import threading
import time
from typing import Any, Callable

from pubsub import pub

from logger_config import logger

from . import Console, Feature

DELIMITER = b"\n"
BUFFER_SIZE = 4096

class Buffer(object):
    def __init__(self, sock: socket.socket, shutdown_server_event: threading.Event):
        self.sock: socket.socket = sock
        self.buffer = b""
        self._shutdown_server_event = shutdown_server_event

    def get_line(self):
        while DELIMITER not in self.buffer and not self._shutdown_server_event.is_set():
            try: 
                data = self.sock.recv(BUFFER_SIZE)
                if not data:  # socket is closed
                    return None
                self.buffer += data
            except TimeoutError:
                pass
        line, sep, self.buffer = self.buffer.partition(DELIMITER)
        return line.decode()

class Yamaha(Console):
    fixed_port = 49280
    type = "Yamaha"
    supported_features = [Feature.CUE_NUMBER]
    _client_socket: socket.socket
    _shutdown_server_event = threading.Event()
    _received_real_data = threading.Event()

    def start_managed_threads(
        self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        self._shutdown_server_event.clear()
        self._received_real_data.clear()
        start_managed_thread("console_connection_thread", self._yamaha_client_thread)
        pub.subscribe(self._shutdown_server_event.set, "shutdown_servers")

    def _yamaha_client_thread(self):
        from app_settings import settings
        while not self._shutdown_server_event.is_set():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.connect((settings.console_ip, self.fixed_port))
                    sock.settimeout(1)
                except(TimeoutError, ConnectionRefusedError, OSError):
                    # There's got to be a better way to get to the outer sleep
                    logger.warning("Could not connect to Yamaha")
                    time.sleep(5000)
                    continue
                logger.info("Connected to Yamaha Console @ {}".format(settings.console_ip))
                buff = Buffer(sock, self._shutdown_server_event)
                while not self._shutdown_server_event.is_set():
                    line = buff.get_line()
                    if line is None:
                        break
                    if line.startswith("NOTIFY sscurrent_ex MIXER:Lib/Scene"):
                        scene_internal_id = line.rsplit(maxsplit=1)[1]
                        logger.info("Yamaha internal scene {} recalled.".format(scene_internal_id))
                        request_scene_info_command = "ssinfo_ex MIXER:Lib/Scene {}\n".format(
                            scene_internal_id
                        )
                        sock.sendall(str.encode(request_scene_info_command))
                    elif line.startswith("OK ssinfo_ex MIXER:Lib/Scene"):
                        quote_split_line = line.split('"')
                        scene_number = quote_split_line[1]
                        scene_name = quote_split_line[3]
                        cue_payload = scene_number + " " + scene_name
                        pub.sendMessage("handle_cue_load", cue=cue_payload)
        logger.info("Closing connection to Yamaha Console")

    def heartbeat(self) -> None:
        pass

