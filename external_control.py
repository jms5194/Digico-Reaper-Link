from typing import Optional

import mido
import mido.backends.rtmidi
from pubsub import pub
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

from constants import PlaybackState, PyPubSubTopics, TransportAction
from logger_config import logger


def external_osc_control():
    from app_settings import settings

    logger.info("Starting external OSC control")
    if settings.external_control_port is None:
        logger.error(
            "External control port is not set. Cannot start external control OSC server."
        )
        return
    else:
        dispatcher = Dispatcher()
        map_osc_external_control_dispatcher(dispatcher)
        server = ThreadingOSCUDPServer(
            ("0.0.0.0", settings.external_control_osc_port), dispatcher
        )
        pub.subscribe(server.shutdown, PyPubSubTopics.SHUTDOWN_SERVERS)
        server.serve_forever()


def map_osc_external_control_dispatcher(dispatcher: Dispatcher) -> None:
    # TODO: Add support for querying current mode and transport state
    for mode in PlaybackState:
        dispatcher.map(f"/markermatic/mode/{mode}", _handle_mode_change, mode)
    for action in TransportAction:
        dispatcher.map(
            f"/markermatic/transport/{action}", _handle_transport_change, action
        )
    dispatcher.map("/markermatic/marker", _handle_marker)


def _handle_mode_change(_: str, mode: str) -> None:
    try:
        playback_state = PlaybackState(mode)
    except ValueError:
        logger.warning("%s is not a supported playback state", mode)
        return
    pub.sendMessage(PyPubSubTopics.CHANGE_PLAYBACK_STATE, selected_mode=playback_state)


def _handle_transport_change(_: str, mode: str) -> None:
    try:
        playback_state = TransportAction(mode)
    except ValueError:
        logger.warning("%s is not a supported transport state", mode)
        return
    pub.sendMessage(PyPubSubTopics.TRANSPORT_ACTION, transport_action=playback_state)


def _handle_marker(_: str, marker_name: Optional[str]) -> None:
    if marker_name is not None:
        pub.sendMessage(PyPubSubTopics.PLACE_MARKER_WITH_NAME, marker_name=marker_name)
    else:
        pub.sendMessage(
            PyPubSubTopics.PLACE_MARKER_WITH_NAME,
            marker_name="Marker from External Control",
        )


def external_midi_control():
    from app_settings import settings

    if (
        settings.external_control_midi_port
        and settings.external_control_midi_port != constants.MIDI_PORT_NONE
    ):
        port = mido.open_input(
            port=settings.external_control_midi_port, callback=_handle_midi_message
        )
        logger.info(f"Opened MIDI port {settings.external_control_midi_port}")
        pub.subscribe(port.close, PyPubSubTopics.SHUTDOWN_SERVERS)
        logger.info("External Midi control started")


def get_midi_ports() -> list[str]:
    # Returns a list of available MIDI input ports.
    try:
        return list(dict.fromkeys(mido.get_input_names()))
    except Exception as e:
        logger.error(f"Error getting MIDI ports: {e}")
        return []


def _handle_midi_message(message: mido.Message) -> None:
    # First, test if the incoming midi is a MMC commmand
    logger.info(f"Received MIDI message: {message}")
    from app_settings import settings

    if settings.mmc_control_enabled:
        if message.type == "sysex":
            if message.hex() == "F0 7F 06 02 F7":
                # If MMC Play is received, send a play command
                logger.info("Received MMC Play command")
                pub.sendMessage(
                    PyPubSubTopics.TRANSPORT_ACTION,
                    transport_action=TransportAction.PLAY,
                )
            elif message.hex() == "F0 7F 06 03 F7":
                logger.info("Received MMC Stop command")
                # If MMC Stop is received, send a stop command
                pub.sendMessage(
                    PyPubSubTopics.TRANSPORT_ACTION,
                    transport_action=TransportAction.STOP,
                )
            elif message.hex() == "F0 7F 06 06 F7":
                logger.info("Received MMC Record command")
                # If MMC Record is received, send a record command
                pub.sendMessage(
                    PyPubSubTopics.TRANSPORT_ACTION,
                    transport_action=TransportAction.RECORD,
                )
        else:
            pass
            """
            # Implement logic here to use captured midi messages. 

            cur_play_msg = mido.Message.from_bytes(settings.midi_play_message)
            cur_stop_msg = mido.Message.from_bytes(settings.midi_stop_message)
            cur_rec_msg = mido.Message.from_bytes(settings.midi_record_message)
            cur_marker_msg = mido.Message.from_bytes(settings.midi_marker_message)
            if message == cur_play_msg:
                pub.sendMessage("incoming_transport_action", transport_action=TransportAction.PLAY)
            elif message == cur_stop_msg:
                pub.sendMessage("incoming_transport_action", transport_action=TransportAction.STOP)
            elif message == cur_rec_msg:
                pub.sendMessage("incoming_transport_action", transport_action=TransportAction.RECORD)
            elif message == cur_marker_msg:
                pub.sendMessage("place_marker_with_name", marker_name="Marker from MIDI")
            """
