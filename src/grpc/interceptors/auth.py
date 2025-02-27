import grpc
from typing import Dict, Any, Callable
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """认证拦截器"""

    def __init__(self):
        self.config = Config()
        self.auth_config = self.config._config.get('auth', {})
        self.tokens = self.auth_config.get('tokens', {})
        self.clients = self.auth_config.get('clients', {})

    async def intercept_service(
            self,
            continuation: Callable,
            handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        """拦截服务调用进行认证"""
        try:
            # 获取认证信息
            auth_header = None
            client_id = None

            for key, value in handler_call_details.invocation_metadata:
                if key == 'authorization':
                    auth_header = value
                elif key == 'client-id':
                    client_id = value

            # 基本验证
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid authorization header")
                return self._failed_handler('Missing or invalid authorization header')

            if not client_id:
                logger.warning("Missing client ID")
                return self._failed_handler('Missing client ID')

            # 获取令牌
            token = auth_header.split(' ')[1]

            # 验证令牌
            token_info = self.tokens.get(token)
            if not token_info:
                logger.warning(f"Invalid token: {token}")
                return self._failed_handler('Invalid token')

            # 验证客户端ID
            if token_info['client_id'] != client_id:
                logger.warning(f"Client ID mismatch: {client_id}")
                return self._failed_handler('Invalid client ID')

            # 验证客户端权限
            method_name = handler_call_details.method.split('/')[-1]
            if method_name not in token_info['permissions']:
                logger.warning(f"Unauthorized method: {method_name}")
                return self._failed_handler('Unauthorized method')

            # 继续处理请求
            return await continuation(handler_call_details)

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._failed_handler(str(e))

    def _failed_handler(self, details: str) -> grpc.RpcMethodHandler:
        """创建一个失败的处理器"""

        def failed(request: Any, context: grpc.ServicerContext) -> None:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, details)

        return grpc.unary_unary_rpc_method_handler(failed)