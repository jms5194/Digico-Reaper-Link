from .console import Console, Feature
from .behringerxair import BehringerXAir
from .digico import DiGiCo
from .studervista import StuderVista
from .yamaha import Yamaha

CONSOLES = {
    "Behringer X Air": BehringerXAir,
    "DiGiCo": DiGiCo,
    "Studer Vista": StuderVista,
    "Yamaha": Yamaha,
}

__all__ = [
    "Console",
    "CONSOLES",
    "Feature",
    "BehringerXAir",
    "DiGiCo",
    "StuderVista",
    "Yamaha",
]
