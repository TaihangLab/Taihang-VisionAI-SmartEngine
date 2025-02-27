from abc import ABC, abstractmethod
from typing import List, Dict, Any

from src.core.config import Config

import warnings
from functools import wraps

def deprecated(func):
    """标记方法为弃用的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"Method {func.__name__} is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return wrapper
class BaseAnomalyAnalyzer(ABC):
    def __init__(self):
        self.detections_buffer = {}
        self.config = Config()

    @abstractmethod
    def add_detection(self, task_id: str, detections: List[Dict[str, Any]], timestamp: float) -> None:
        pass

    @abstractmethod
    def check_anomalies(self, task_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_statistics(self, task_id: str) -> Dict[str, Any]:
        pass

    @deprecated
    @abstractmethod
    def is_anomaly(self, detection: Dict[str, Any]) -> bool:
        """
        判断单个检测结果是否异常
        @deprecated: 此方法已弃用，请使用 check_anomalies 方法代替
        """
        pass

