import datetime
from enum import StrEnum

APPLICATION_NAME = "MarkerMatic"
APPLICATION_NAME_LEGACY = "Digico-Reaper Link"
APPLICATION_AUTHOR = "Justin Stasiw"
APPLICATION_DESCRIPTION = (
    "A tool to automate cueing and marker placement between consoles and DAWs"
)
APPLICATION_COPYRIGHT = "© {} Justin Stasiw and Liam Steckler".format(
    datetime.datetime.now().year
)
BUNDLE_IDENTIFIER = "com.justinstasiw.markermatic"
CREDITS = "Solar Icons by 480 Design is licensed under CC BY 4.0"
CONFIG_FILENAME = "settingsV3.ini"
LOG_FILENAME = "MarkerMatic.log"
VERSION = "4.0.0"
WEBSITE = "https://markermatic.com"


class PlaybackState(StrEnum):
    RECORDING = "recording"
    PLAYBACK_TRACK = "playback-track"
    PLAYBACK_NO_TRACK = "playback-no-track"


class TransportAction(StrEnum):
    PLAY = "play"
    STOP = "stop"
    RECORD = "record"
