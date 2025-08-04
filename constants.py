from enum import Enum, auto

APPLICATION_NAME = "MarkerMatic"
APPLICATION_NAME_LEGACY = "Digico-Reaper Link"
APPLICATION_AUTHOR = "Justin Stasiw"
APPLICATION_ABOUT = "A tool to automate cueing and marker placement between consoles and DAWs. Written by Justin Stasiw & Liam Steckler."
BUNDLE_IDENTIFIER = "com.justinstasiw.markermatic"
CONFIG_FILENAME = "settingsV3.ini"
LOG_FILENAME = "MarkerMatic.log"


class PlaybackState(Enum):
    RECORDING = auto()
    PLAYBACK_TRACK = auto()
    PLAYBACK_NO_TRACK = auto()
