import time
from functools import wraps
from typing import Dict, Any, Optional
import prometheus_client as prom
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 定义Prometheus指标
REQUEST_TIME = prom.Summary(
    'request_processing_seconds',
    'Time spent processing request',
    ['method']
)

INFERENCE_TIME = prom.Histogram(
    'model_inference_seconds',
    'Time spent on model inference',
    ['model_name'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

ERROR_COUNTER = prom.Counter(
    'error_total',
    'Total number of errors',
    ['type']
)

class MetricsCollector:
    """
    指标收集器
    用于收集和导出性能指标
    """
    def __init__(self, export_port: int = 8000):
        self.export_port = export_port
        self._start_http_server()

    def _start_http_server(self):
        """启动Prometheus指标导出服务器"""
        try:
            prom.start_http_server(self.export_port)
            logger.info(f"Metrics server started on port {self.export_port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {str(e)}")

    @staticmethod
    def time_request(method: str):
        """
        请求时间装饰器
        记录请求处理时间
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                result = await func(*args, **kwargs)
                REQUEST_TIME.labels(method=method).observe(time.time() - start_time)
                return result
            return wrapper
        return decorator

    @staticmethod
    def time_inference(model_name: str):
        """
        推理时间装饰器
        记录模型推理时间
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                result = await func(*args, **kwargs)
                INFERENCE_TIME.labels(model_name=model_name).observe(
                    time.time() - start_time
                )
                return result
            return wrapper
        return decorator

    @staticmethod
    def count_error(error_type: str):
        """
        错误计数装饰器
        记录错误次数
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    ERROR_COUNTER.labels(type=error_type).inc()
                    raise
            return wrapper
        return decorator

    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """
        获取当前指标数据
        """
        return {
            'request_time': REQUEST_TIME._samples(),
            'inference_time': INFERENCE_TIME._samples(),
            'error_count': ERROR_COUNTER._samples()
        } 