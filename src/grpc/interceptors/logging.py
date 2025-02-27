import time
import grpc
from typing import Callable, Any
from src.utils.logger import setup_logger
from src.utils.metrics import MetricsCollector

logger = setup_logger(__name__)


class LoggingInterceptor(grpc.aio.ServerInterceptor):
    """日志拦截器"""

    def __init__(self):
        self.metrics = MetricsCollector()

    async def intercept_service(
            self,
            continuation: Callable,
            handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """拦截服务调用并记录日志"""
        start_time = time.time()
        method = handler_call_details.method

        metadata = {}
        for key, value in handler_call_details.invocation_metadata:
            metadata[key] = value

        client_id = metadata.get('client-id', 'unknown')
        request_id = metadata.get('request-id', 'unknown')

        logger.info(
            f"Request started | "
            f"method={method} | "
            f"client_id={client_id} | "
            f"request_id={request_id} | "
            f"metadata={metadata}"
        )

        try:
            handler = await continuation(handler_call_details)

            if handler is None:
                logger.error(
                    f"Request handler not found | "
                    f"method={method} | "
                    f"client_id={client_id}"
                )
                return None

            duration = (time.time() - start_time) * 1000

            logger.info(
                f"Request completed | "
                f"method={method} | "
                f"client_id={client_id} | "
                f"request_id={request_id} | "
                f"duration={duration:.2f}ms | "
                f"status=success"
            )

            # 正确使用metrics装饰器
            @self.metrics.time_request(method)
            async def record_time():
                pass

            await record_time()

            return handler

        except Exception as e:
            duration = (time.time() - start_time) * 1000

            logger.error(
                f"Request failed | "
                f"method={method} | "
                f"client_id={client_id} | "
                f"request_id={request_id} | "
                f"duration={duration:.2f}ms | "
                f"status=error | "
                f"error={str(e)}"
            )

            # 正确使用metrics装饰器
            @self.metrics.count_error("grpc_error")
            async def record_error():
                pass

            await record_error()

            raise