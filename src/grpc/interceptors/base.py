import grpc
from typing import Any, Callable

class AsyncServerInterceptor(grpc.aio.ServerInterceptor):
    """异步服务器拦截器基类"""

    async def intercept_service(
        self,
        continuation: Callable,
        handler_call_details: grpc.HandlerCallDetails
    ) -> grpc.RpcMethodHandler:
        """拦截服务调用"""
        handler = await continuation(handler_call_details)
        if handler:
            return handler
        return None 