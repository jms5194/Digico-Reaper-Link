from . import Console, Feature


class DiGiCo(Console):
    type = "DiGiCo"
    supported_features = [Feature.CUE_NUMBER, Feature.REPEATER]
