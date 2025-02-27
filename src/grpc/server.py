import asyncio # Python的异步IO库
import uuid

import grpc  # gRPC库
from concurrent import futures  # Python的concurrent.futures库提供了ThreadPoolExecutor和ProcessPoolExecutor两个执行器，可以用来在单独的线程或进程中执行任务
from typing import Dict, List

# 导入自定义模块
from src.core.config import Config # 导入Config类
from src.utils.logger import setup_logger, LoggerMixin, log_exception # 导入自定义的日志模块
from src.grpc.interceptors.auth import AuthInterceptor # 导入AuthInterceptor拦截器
from src.grpc.interceptors.logging import LoggingInterceptor # 导入LoggingInterceptor拦截器
from src.utils.metrics import MetricsCollector # 导入MetricsCollector类
from src.grpc.interceptors.rate_limit import RateLimitInterceptor # 导入RateLimitInterceptor拦截器

# 导入生成的 Skill Service 代码
from protos.ts_scripts import skill_pb2, skill_pb2_grpc

from src.messaging.task_processor import TaskProcessor
from protos.ts_scripts import task_pb2, task_pb2_grpc  # 添加导入


# 设置日志
logger = setup_logger(__name__)

class TaskServicer(task_pb2_grpc.TaskServiceServicer):
    def __init__(self):
        self.processor = TaskProcessor()

    async def StartTask(self, request, context):
        try:
            task_id = str(uuid.uuid4())
            asyncio.create_task(self.processor.process_task(task_id, request))
            return task_pb2.TaskResponse(
                task_id=task_id,
                status="started",
                message="Task started successfully",
                error_code=0
            )
        except Exception as e:
            logger.error(f"Error starting task: {e}")
            return task_pb2.TaskResponse(
                status="error",
                message=str(e),
                error_code=1
            )

    async def StopTask(self, request, context):
        try:
            await self.processor.stop_task(request.task_id)
            return task_pb2.TaskResponse(
                task_id=request.task_id,
                status="stopped",
                message="Task stopped successfully",
                error_code=0
            )
        except Exception as e:
            logger.error(f"Error stopping task: {e}")
            return task_pb2.TaskResponse(
                status="error",
                message=str(e),
                error_code=1
            )

class SkillServicer(skill_pb2_grpc.SkillServiceServicer):
    """技能服务实现"""
    
    def __init__(self):
        self.config = Config()
        self.skills = self.config.skills
        
    async def ListSkills(
        self,
        request: skill_pb2.ListSkillsRequest,
        context: grpc.aio.ServicerContext
    ) -> skill_pb2.ListSkillsResponse:
        """列出所有可用的技能"""
        try:
            skills = []
            
            for skill_id, skill_config in self.skills.items():
                # 应用过滤条件
                if request.HasField('type') and request.type != skill_config['type']:
                    continue
                if request.HasField('enabled') and request.enabled != skill_config['enabled']:
                    continue
                
                # 构造技能信息
                skill = skill_pb2.SkillInfo(
                    id=skill_id,
                    name=skill_config['name'],
                    type=skill_config['type'],
                    description=skill_config['description'],
                    enabled=skill_config['enabled']
                )
                
                # 添加模型信息
                if skill_config['models']:
                    first_model = skill_config['models'][0]
                    skill.model_name = first_model['name']
                    for key, value in first_model['parameters'].items():
                        skill.parameters[key] = str(value)
                
                skills.append(skill)
            
            return skill_pb2.ListSkillsResponse(skills=skills)
            
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

class AIEngineServer:
    """AI引擎gRPC服务器"""
    
    def __init__(self):
        self.config = Config()
        self.server = None
        
    async def start(self):
        """启动服务器"""
        self.server = grpc.aio.server(
            futures.ThreadPoolExecutor(
                max_workers=self.config.server['max_workers']
            ),
            interceptors=[LoggingInterceptor(),  # 日志拦截器
                          AuthInterceptor(),  # 认证拦截器
                          RateLimitInterceptor()  # 限流拦截器
                          ]
        )
        
        # 注册 Skill 服务
        skill_pb2_grpc.add_SkillServiceServicer_to_server(
            SkillServicer(),
            self.server
        )

        task_pb2_grpc.add_TaskServiceServicer_to_server(  # 添加任务服务
            TaskServicer(),
            self.server
        )
        
        # 添加监听地址
        listen_addr = f"{self.config.server['host']}:{self.config.server['port']}"
        self.server.add_insecure_port(listen_addr)
        
        logger.info(f"Starting server on {listen_addr}")
        await self.server.start()
        
        try:
            await self.server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            await self.server.stop(0)

if __name__ == "__main__":
    server = AIEngineServer()
    asyncio.run(server.start())