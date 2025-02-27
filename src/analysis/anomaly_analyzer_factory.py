from .base_anomaly_analyzer import BaseAnomalyAnalyzer
from .helmet_anomaly_analyzer import HelmetAnomalyAnalyzer
from .ppe_anomaly_analyzer import PPEAnomalyAnalyzer


class AnomalyAnalyzerFactory:
    _analyzers = {
        'helmet_detection': HelmetAnomalyAnalyzer,
        'ppe_detection': PPEAnomalyAnalyzer
    }

    @classmethod
    def create_analyzer(cls, skill_name: str) -> BaseAnomalyAnalyzer:
        analyzer_class = cls._analyzers.get(skill_name)
        if not analyzer_class:
            raise ValueError(f"No anomaly analyzer found for skill: {skill_name}")
        return analyzer_class()