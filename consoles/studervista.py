import socket
import threading
import time
from typing import Any, Callable, List

import asn1
import wx
from pubsub import pub

from logger_config import logger

from . import Console


class StuderVista(Console):
    type = "Studer Vista"
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
            with socket.socket(
                socket.AF_INET, socket.SOCK_STREAM
            ) as self._client_socket:
                try:
                    self._client_socket.connect(
                        (settings.console_ip, settings.console_port)
                    )
                    logger.info("Ember connected successfully")
                except TimeoutError:
                    continue
                self._send_subscribe()
                while not self._shutdown_server_event.is_set():
                    try:
                        result_bytes = self._client_socket.recv(4096)
                    except ConnectionResetError:
                        logger.error("Ember connection reset")
                        pub.sendMessage("console_disconnected")
                        break
                    decoder = asn1.Decoder()
                    decoder.start(result_bytes)
                    _, value = decoder.read()
                    decoded_message = self._decode_message(value)
                    if decoded_message:
                        pub.sendMessage("console_connected", consolename="Connected")
                        self._received_real_data.set()
                        if decoded_message != "Last Recalled Snapshot":
                            decoded_message = decoded_message[-1:][0]
                            pub.sendMessage("handle_cue_load", cue=decoded_message)
            time.sleep(5000)

    def _decode_message(self, value: Any) -> List[str]:
        message_string: List[str] = []
        if type(value) is list:
            for item in value:
                message_string.extend(self._decode_message(item))
        elif value:
            message_string.append(value)
        return message_string

    def _send_subscribe(self) -> None:
        self._client_socket.sendall(
            b"\x7f\x8f\xff\xfe\xd9\\\x800\x80\xa1\x181\x16\xa2\x141\x12\xa1\x101\x0e\xa1\x0c1\n\xe4\x081\x06\x7f \x03\x02\x01\x01\x00\x00\x00\x00"
        )

    def heartbeat(self) -> None:
        if hasattr(self, "_client_socket"):
            try:
                if self._received_real_data.is_set():
                    self._client_socket.sendall(
                        b"\x7f\x8f\xff\xfe\xd9\\\x800\x80\x00\x00\x00\x00"
                    )
                    pub.sendMessage("console_connected", consolename="Connected")
                else:
                    self._send_subscribe()
                    pub.sendMessage(
                        "console_connected", consolename="Starting", colour=wx.YELLOW
                    )
            except OSError:
                pub.sendMessage("console_disconnected")
