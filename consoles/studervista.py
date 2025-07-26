import socket
from typing import Any, Callable, List

import asn1
from pubsub import pub

from logger_config import logger

from . import Console


class StuderVista(Console):
    type = "Studer Vista"
    supported_features = []
    client_socket: socket.socket

    def start_managed_threads(
        self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        start_managed_thread("console_connection_thread", self._console_client_thread)
        # TODO: Handling exiting this thread properly

    def _console_client_thread(self):
        from app_settings import settings

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.client_socket:
            try:
                self.client_socket.connect((settings.console_ip, settings.console_port))
                logger.info("Connected successfully")
            except TimeoutError:
                logger.error("Could not connect via Ember")
                return
            self._send_subscribe()
            while True:
                try:
                    result_bytes = self.client_socket.recv(10000000)
                except ConnectionResetError:
                    logger.error("Ember connection closed")
                    pub.sendMessage("console_disconnected")
                decoder = asn1.Decoder()
                decoder.start(result_bytes)
                _, value = decoder.read()
                decoded_message = self._decode_message(value)
                if len(decoded_message) > 0:
                    decoded_message = decoded_message[-1:][0]
                    pub.sendMessage("handle_cue_load", cue=decoded_message)

    def _decode_message(self, value: Any) -> List[str]:
        message_string: List[str] = []
        if type(value) is list:
            for item in value:
                message_string.extend(self._decode_message(item))
        elif value:
            message_string.append(value)
        return message_string

    def _send_subscribe(self) -> None:
        if isinstance(self.client_socket, socket.socket):
            self.client_socket.sendall(
                b"\x7f\x8f\xff\xfe\xd9\\\x800\x80\xa1\x181\x16\xa2\x141\x12\xa1\x101\x0e\xa1\x0c1\n\xe4\x081\x06\x7f \x03\x02\x01\x01\x00\x00\x00\x00"
            )

    def heartbeat(self) -> bool:
        try:
            self.client_socket.sendall(
                b"\x7f\x8f\xff\xfe\xd9\\\x800\x80\x00\x00\x00\x00"
            )
            return True
        except Exception:
            return False
