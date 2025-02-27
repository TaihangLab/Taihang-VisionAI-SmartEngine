import asyncio
import grpc
import time
from typing import List, Optional

from protos.ts_scripts import skill_pb2, skill_pb2_grpc
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SkillClient:
    """Skill服务测试客户端"""

    def __init__(self, host: str = "localhost", port: int = 50051):
        self.channel = None
        self.stub = None
        self.server_addr = f"{host}:{port}"

    async def connect(self):
        """连接服务器"""
        try:
            self.channel = grpc.aio.insecure_channel(self.server_addr)
            self.stub = skill_pb2_grpc.SkillServiceStub(self.channel)
            logger.info(f"Connected to server at {self.server_addr}")
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            raise

    async def close(self):
        """关闭连接"""
        if self.channel:
            await self.channel.close()
            logger.info("Connection closed")

    async def list_skills(
            self,
            skill_type: Optional[str] = None,
            enabled: Optional[bool] = None
    ) -> List[dict]:
        """获取技能列表"""
        try:
            # 构造请求
            request = skill_pb2.ListSkillsRequest()
            if skill_type:
                request.type = skill_type
            if enabled is not None:
                request.enabled = enabled

            # 添加元数据
            metadata = [
                ("authorization", "Bearer test_token_dev"),
                ("client-id", "vision_ai_client_dev")
            ]

            # 发送请求
            response = await self.stub.ListSkills(request, metadata=metadata)

            # 转换响应
            return [
                {
                    'id': skill.id,
                    'name': skill.name,
                    'type': skill.type,
                    'description': skill.description,
                    'model_name': skill.model_name,
                    'enabled': skill.enabled,
                    'parameters': dict(skill.parameters)
                }
                for skill in response.skills
            ]

        except grpc.RpcError as e:
            logger.error(f"RPC failed: {e}")
            raise


async def main():
    """测试主函数"""
    client = SkillClient()

    try:
        await client.connect()

        logger.info("Testing: List all skills")
        skills = await client.list_skills()
        logger.info(f"All skills: {skills}")

    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())