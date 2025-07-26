from .console import Console, Feature


class Digico(Console):
    type = "Digico"
    supported_features = [Feature.CUE_NUMBER, Feature.REPEATER]
