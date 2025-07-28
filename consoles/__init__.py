from .console import Console, Feature
from .digico import DiGiCo
from .studervista import StuderVista

CONSOLES = {"DiGiCo": DiGiCo, "Studer Vista": StuderVista}

__all__ = ["Console", "CONSOLES", "Feature", "DiGiCo", "StuderVista"]
