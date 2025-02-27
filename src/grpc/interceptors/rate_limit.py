import time
import grpc
from typing import Dict,Callable,Tuple
from collections import defaultdict
from src.core.config import Config
from src.grpc.interceptors.base import AsyncServerInterceptor

class RateLimiter:
    """
    速率限制器
    使用令牌桶算法实现请求限制
    """
    def __init__(self, max_requests: int, period: int):
        self.max_requests = max_requests  # 最大请求数
        self.period = period  # 时间周期(秒)
        self.requests = []    # 请求时间列表
        
    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        now = time.time()
        
        # 移除过期的请求记录
        while self.requests and now - self.requests[0] >= self.period:
            self.requests.pop(0)
            
        # 检查是否超过限制
        if len(self.requests) >= self.max_requests:
            return False
            
        # 记录新请求
        self.requests.append(now)
        return True

class RateLimitInterceptor(AsyncServerInterceptor):
    """
    速率限制拦截器
    限制请求频率
    """
    def __init__(self):
        self.config = Config()
        self.limiters: Dict[str, RateLimiter] = {}
        
        # 创建默认限制器
        default_config = self.config.rate_limit['default']
        self.default_limiter = RateLimiter(
            default_config['requests'],
            default_config['period']
        )
        
        # 创建方法特定的限制器
        for method, config in self.config.rate_limit.get('methods', {}).items():
            self.limiters[method] = RateLimiter(
                config['requests'],
                config['period']
            )

    async def intercept_service(
        self,
        continuation: Callable,
        handler_call_details: grpc.HandlerCallDetails
    ) -> grpc.RpcMethodHandler:
        """
        拦截服务调用
        检查请求是否超过限制
        """
        method = handler_call_details.method
        
        # 获取对应的限制器
        limiter = self.limiters.get(method, self.default_limiter)
        
        # 检查是否允许请求
        if not limiter.is_allowed():
            return self._reject_request()
            
        # 继续处理请求
        return await continuation(handler_call_details)

    def _reject_request(self) -> grpc.RpcMethodHandler:
        """拒绝请求"""
        async def reject(request, context):
            await context.abort(
                grpc.StatusCode.RESOURCE_EXHAUSTED,
                'Too many requests'
            )
        
        return grpc.unary_unary_rpc_method_handler(reject) 