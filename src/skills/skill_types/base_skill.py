from typing import Dict, Any
from abc import ABC, abstractmethod
import grpc
from protos.ts_scripts.torchserve_grpc_client import (
    get_inference_stub,
    get_management_stub,
    register,
    unregister,
    infer
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class BaseSkill(ABC):
    """技能基类"""
    def __init__(self, skill_id: str, config: Dict[str, Any]):
        self.skill_id = skill_id
        self.config = config
        self.models = {}  # 存储模型配置
        self.model_tasks = {}  # 记录模型使用情况
        self._init_models()

    def _init_models(self):
        """初始化模型配置"""
        for model_config in self.config.get('models', []):
            # 使用model_id作为唯一标识
            model_id = model_config['model_id']
            self.models[model_id] = {
                'name': model_config['name'],
                'type': model_config['type'],
                'parameters': model_config.get('parameters', {}),
                'mar_path': model_config.get('mar_path'),
                'active': False
            }
            self.model_tasks[model_id] = set()

    async def add_task(self, task_id: str):
        """添加任务并按需启动模型"""
        for model_name in self.models:
            self.model_tasks[model_name].add(task_id)
            if len(self.model_tasks[model_name]) == 1:
                await self._start_model(model_name)

    async def remove_task(self, task_id: str):
        """移除任务并按需停止模型"""
        for model_name in self.models:
            if task_id in self.model_tasks[model_name]:
                self.model_tasks[model_name].remove(task_id)
                if not self.model_tasks[model_name]:
                    await self._stop_model(model_name)

    async def _start_model(self, model_name: str):
        """启动模型"""
        try:
            if not self.models[model_name]['active']:
                management_stub = get_management_stub()
                mar_path = self.models[model_name]['mar_path']
                await register(management_stub, model_name, mar_path)
                self.models[model_name]['active'] = True
                logger.info(f"Model {model_name} started successfully")
        except Exception as e:
            logger.error(f"Failed to start model {model_name}: {str(e)}")
            raise

    async def _stop_model(self, model_name: str):
        """停止模型"""
        try:
            if self.models[model_name]['active']:
                management_stub = get_management_stub()
                await unregister(management_stub, model_name)
                self.models[model_name]['active'] = False
                logger.info(f"Model {model_name} stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop model {model_name}: {str(e)}")
            raise

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能"""
        pass

    @abstractmethod
    async def validate(self) -> bool:
        """验证技能配置"""
        pass

    def is_model_in_use(self, model_name: str) -> bool:
        """检查模型是否正在被使用"""
        return bool(self.model_tasks.get(model_name))

    def get_model_tasks(self, model_name: str) -> set:
        """获取使用某个模型的所有任务"""
        return self.model_tasks.get(model_name, set())