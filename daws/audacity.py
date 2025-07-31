import json
from . import Daw
from pubsub import pub
from logger_config import logger
from typing import Any, Callable
import threading
import os
import sys
import pyperclip



class Audacity(Daw):
    type = "Audacity"
    _shutdown_server_event = threading.Event()

    def __init__(self):
        super().__init__()
        self.audacity_send_lock = threading.Lock()
        self.to_name = None
        self.from_name = None
        self.eol = None
        self.to_file = None
        self.from_file = None
        pub.subscribe(self._place_marker_with_name, "place_marker_with_name")
        pub.subscribe(self._incoming_transport_action, "incoming_transport_action")
        pub.subscribe(self._handle_cue_load, "handle_cue_load")
        pub.subscribe(self._shutdown_servers, "shutdown_servers")
        pub.subscribe(self._shutdown_server_event.set, "shutdown_servers")

    def start_managed_threads(
            self, start_managed_thread: Callable[[str, Any], None]
    ) -> None:
        self._shutdown_server_event.clear()
        logger.info("Starting Audacity Connection thread")
        start_managed_thread(
            "daw_connection_thread", self._build_audacity_connection_pipe
        )

    def _build_audacity_connection_pipe(self):
        # Build path for pipes- os dependent
        if sys.platform == 'win32':
            self.to_name = '\\\\.\\pipe\\ToSrvPipe'
            self.from_name = '\\\\.\\pipe\\FromSrvPipe'
            self.eol = '\r\n\0'
        else:
            self.to_name = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
            self.from_name = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
            self.eol = '\n'

        if not os.path.exists(self.to_name) and os.path.exists(self.from_name):
            logger.error("Audacity is not properly configured for pipe operation")
        else:
            logger.info("Pipe connection to Audacity has been confirmed viable")

        self.to_file = open(self.to_name, 'w')
        print("-- File to write to has been opened")
        self.from_file = open(self.from_name, 'rt')
        print("-- File to read from has now been opened too\r\n")

    def send_command(self, command):
        # Send a single command.
        print("Send: >>> \n" + command)
        self.to_file.write(command + self.eol)
        self.to_file.flush()

    def get_response(self):
        # Return the command response.
        result = ''
        line = ''
        while True:
            result += line
            line = self.from_file.readline()
            if line == '\n' and len(result) > 0:
                break
        return result

    def do_command(self, command):
        # Send one command, and return the response.
        self.send_command(command)
        response = self.get_response()
        print("Rcvd: <<< \n" + response)
        return response

    def _place_marker_with_name(self, marker_name):
        with self.audacity_send_lock:
            pyperclip.copy(marker_name)
            self.send_command("GetInfo: Type=Selection")
            audacity_response = self.get_response()
            audacity_response= audacity_response[:-26]
            print(audacity_response)
            audacity_cur_pos = json.loads(audacity_response)
            print(audacity_cur_pos)


    def _incoming_transport_action(self, transport_action):
        try:
            if transport_action == "play":
                self._audacity_play()
            elif transport_action == "stop":
                self._audacity_stop()
            elif transport_action == "rec":
                self._audacity_rec()
        except Exception as e:
            logger.error(f"Error processing transport macros: {e}")

    def _audacity_play(self):
        with self.audacity_send_lock:
            self.do_command("Play")

    def _audacity_stop(self):
        with self.audacity_send_lock:
            self.do_command("Stop")

    def _audacity_rec(self):
        # Sends action to skip to end of project and then record, to prevent overwrites
        from app_settings import settings
        settings.marker_mode = "Recording"
        pub.sendMessage("mode_select_osc", selected_mode="Recording")
        with self.audacity_send_lock:
            self.do_command("Record1stChoice")

    def _handle_cue_load(self):
        pass

    def _shutdown_servers(self):
        pass
