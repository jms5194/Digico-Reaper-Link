from .console import Console, Feature
from .digico import DiGiCo
from .studervista import StuderVista
from .yamaha import Yamaha

CONSOLES = {"DiGiCo": DiGiCo, "Studer Vista": StuderVista, "Yamaha": Yamaha}

__all__ = ["Console", "CONSOLES", "Feature", "DiGiCo", "StuderVista", "Yamaha"]
