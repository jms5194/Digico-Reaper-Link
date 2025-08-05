from typing import Optional

from pubsub import pub
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer

from constants import PlaybackState, TransportAction
from logger_config import logger
import mido


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

def external_midi_control():
    from app_settings import settings
    logger.info("Starting external MIDI control")
    if settings.external_control_midi_port is not None:
        try:
            mido.open_input(port=settings.external_control_midi_port, callback=_handle_midi_message)
            logger.info(f"Opened MIDI port {settings.external_control_midi_port}")
        except Exception as e:
            logger.error(f"Failed to open MIDI port {settings.external_control_midi_port}: {e}")

def get_midi_ports() -> list[str]:
    """Returns a list of available MIDI input ports."""
    try:
        return mido.get_input_names()
    except Exception as e:
        logger.error(f"Error getting MIDI ports: {e}")
        return []

def _handle_midi_message(message: mido.Message) -> None:
    # First, test if the incoming midi is a MMC commmand
    self.logger.info(f"Received MIDI message: {message}")
    from app_settings import settings
    if settings.mmc_control_enabled is "True":
        if message.type == "sysex":
            if message.hex() == "f0 7f 06 02 f7":
                # If MMC Play is received, send a play command
                logger.info("Received MMC Play command")    
                pub.sendMessage("incoming_transport_action", transport_action=TransportAction.PLAY)
            elif message.hex() == "f0 7f 06 03 f7":
                logger.info("Received MMC Stop command")    
                # If MMC Stop is received, send a stop command
                pub.sendMessage("incoming_transport_action", transport_action=TransportAction.STOP)
            elif message.hex() == "f0 7f 06 06 f7":
                logger.info("Received MMC Record command")  
                # If MMC Record is received, send a record command
                pub.sendMessage("incoming_transport_action", transport_action=TransportAction.RECORD)
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
