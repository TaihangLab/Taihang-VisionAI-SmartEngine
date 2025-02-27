import asyncio

from src.grpc.server import AIEngineServer
from src.messaging.task_processor import TaskProcessor

if __name__ == "__main__":
    # 创建AI引擎服务
    server = AIEngineServer()

    # 创建任务处理器
    processor = TaskProcessor()  # 更新类名
    try:
        asyncio.run(server.start())
        asyncio.run(processor.start())
    except KeyboardInterrupt:
        asyncio.run(processor.stop())
        asyncio.run(server.stop())
        print("AI Engine stopped!")