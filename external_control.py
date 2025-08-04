from typing import Optional

from pubsub import pub
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

from constants import PlaybackState, TransportAction
from logger_config import logger


def external_osc_control():
    dispatcher = Dispatcher()
    map_osc_external_control_dispatcher(dispatcher)
    server = ThreadingOSCUDPServer(("0.0.0.0", 48428), dispatcher)
    pub.subscribe(server.shutdown, "shutdown_servers")
    server.serve_forever()


def map_osc_external_control_dispatcher(dispatcher: Dispatcher) -> None:
    dispatcher.map("/markermatic/v4/mode", _handle_mode_change)
    dispatcher.map("/markermatic/v4/transport", _handle_transport_change)
    dispatcher.map("/markermatic/v4/marker", _handle_marker)


def _handle_mode_change(_: str, mode: str) -> None:
    try:
        playback_state = PlaybackState(mode)
    except ValueError:
        logger.warning("%s is not a supported playback state", mode)
        return
    pub.sendMessage("mode_select_osc", selected_mode=playback_state)


def _handle_transport_change(_: str, mode: str) -> None:
    try:
        playback_state = TransportAction(mode)
    except ValueError:
        logger.warning("%s is not a supported transport state", mode)
        return
    pub.sendMessage("incoming_transport_action", transport_action=playback_state)


def _handle_marker(_: str, marker_name: Optional[str]) -> None:
    if marker_name is not None:
        pub.sendMessage("place_marker_with_name", marker_name=marker_name)
    else:
        pub.sendMessage("place_marker_with_name", marker_name="Marker from Console")
