import pytest
import asyncio
import grpc
from pathlib import Path
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.grpc.server import AIEngineServer
from src.models.model_service import ModelService
from src.skills.skill_orchestrator import SkillOrchestrator
from src.messaging.task_processor import MessageProcessor

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def grpc_server():
    """启动gRPC服务器"""
    server = AIEngineServer()
    await server.start()
    yield server
    await server.stop()

@pytest.fixture(scope="session")
async def grpc_channel():
    """创建gRPC通道"""
    channel = grpc.aio.insecure_channel('localhost:50051')
    yield channel
    await channel.close()

@pytest.fixture
def model_service():
    """创建模型服务实例"""
    return ModelService()

@pytest.fixture
def skill_orchestrator():
    """创建技能编排器实例"""
    return SkillOrchestrator()

@pytest.fixture
def message_processor():
    """创建消息处理器实例"""
    return MessageProcessor() 