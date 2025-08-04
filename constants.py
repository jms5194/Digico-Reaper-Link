from enum import StrEnum

APPLICATION_NAME = "MarkerMatic"
APPLICATION_NAME_LEGACY = "Digico-Reaper Link"
APPLICATION_AUTHOR = "Justin Stasiw"
APPLICATION_ABOUT = "A tool to automate cueing and marker placement between consoles and DAWs. Written by Justin Stasiw & Liam Steckler."
BUNDLE_IDENTIFIER = "com.justinstasiw.markermatic"
CONFIG_FILENAME = "settingsV3.ini"
LOG_FILENAME = "MarkerMatic.log"


class PlaybackState(StrEnum):
    RECORDING = "recording"
    PLAYBACK_TRACK = "playback-track"
    PLAYBACK_NO_TRACK = "playback-no-track"


class TransportAction(StrEnum):
    PLAY = "play"
    STOP = "stop"
    RECORD = "record"

