import socket
import threading
import time
from typing import Any, Callable, List
from pubsub import pub
from logger_config import logger
from . import Console

YAMAHA_PORT = 49280
DELIMITER = b"\n"
BUFFER_SIZE = 4096

class Buffer(object):
    def __init__(self, sock):
        self.sock = sock
        self.buffer = b""

    def get_line(self):
        while DELIMITER not in self.buffer:
            data = self.sock.recv(BUFFER_SIZE)
            if not data:  # socket is closed
                return None
            self.buffer += data
        line, sep, self.buffer = self.buffer.partition(DELIMITER)
        return line.decode()


class Yamaha(Console):
    type = "Yamaha"
    supported_features = []
    _client_socket: socket.socket
    _shutdown_server_event = threading.Event()
    _received_real_data = threading.Event()

    def start_managed_threads(
        self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        self._shutdown_server_event.clear()
        self._received_real_data.clear()
        start_managed_thread("console_connection_thread", self._console_client_thread)
        pub.subscribe(self._shutdown_server_event.set, "shutdown_servers")

    def _console_client_thread(self):
        from app_settings import settings

        while not self._shutdown_server_event.is_set():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((settings.console_ip, YAMAHA_PORT))
                logger.info("Connected to Yamaha Console @{}".format(settings.console_ip))
                buff = Buffer(sock)
                while True:
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
                        logger.info("Generating marker with number {} and name {}.".format(scene_number, scene_name))

                    pub.sendMessage("place_marker_with_name", marker_name=scene_number + " " + scene_name)




    def heartbeat(self) -> None:
        pass

