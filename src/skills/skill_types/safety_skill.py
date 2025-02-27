from typing import Dict, Any
import grpc
from src.skills.skill_types.base_skill import BaseSkill
from src.core.exceptions import SkillError
from protos.ts_scripts.torchserve_grpc_client import (
    get_inference_stub,
    get_management_stub,
    register,
    unregister,
    infer
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class SafetySkill(BaseSkill):
    def __init__(self, skill_id: str, config: Dict[str, Any]):
        super().__init__(skill_id, config)
        self.models = {}
        self.model_tasks = {}  # 记录每个模型被哪些任务使用
        self.stub = None
        self._init_models()

    def _init_models(self):
        """初始化模型配置"""
        for model_config in self.config.get('models', []):
            model_name = model_config['name']
            self.models[model_name] = {
                'type': model_config['type'],
                'parameters': model_config.get('parameters', {}),
                'mar_path': model_config.get('mar_path'),
                'active': False
            }
            self.model_tasks[model_name] = set()  # 初始化模型的任务集合

    async def add_task(self, task_id: str):
        """添加任务并按需启动模型"""
        for model_name in self.models:
            self.model_tasks[model_name].add(task_id)
            # 如果是模型的第一个任务,启动模型
            if len(self.model_tasks[model_name]) == 1:
                await self._start_model(model_name)

    async def remove_task(self, task_id: str):
        """移除任务并按需停止模型"""
        for model_name in self.models:
            # 从模型的任务集合中移除
            self.model_tasks[model_name].discard(task_id)
            # 如果模型没有任务了,停止模型
            if not self.model_tasks[model_name]:
                await self._stop_model(model_name)

    async def _start_model(self, model_name: str):
        """启动模型"""
        if not self.stub:
            self.stub = get_management_stub()

        model_info = self.models.get(model_name)
        if not model_info or model_info['active']:
            return

        try:
            register(
                self.stub,
                model_name,
                model_info['mar_path'],
                metadata=(('protocol', 'gRPC'), ('session_id', '12345'))
            )
            model_info['active'] = True
            logger.info(f"Model {model_name} started")
        except Exception as e:
            raise SkillError(f"Failed to start model {model_name}: {str(e)}")

    async def _stop_model(self, model_name: str):
        """停止模型"""
        model_info = self.models.get(model_name)
        if not model_info or not model_info['active']:
            return

        # 确保没有任务在使用此模型
        if not self.model_tasks[model_name]:
            try:
                unregister(
                    self.stub,
                    model_name,
                    metadata=(('protocol', 'gRPC'), ('session_id', '12345'))
                )
                model_info['active'] = False
                logger.info(f"Model {model_name} stopped")
            except Exception as e:
                logger.error(f"Failed to stop model {model_name}: {str(e)}")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行模型推理"""
        task_id = input_data.get('task_id')
        frame = input_data.get('frame')
        if not frame:
            raise SkillError("Frame data is required")

        # 确保任务已注册
        if not any(task_id in tasks for tasks in self.model_tasks.values()):
            await self.add_task(task_id)

        results = {}
        inference_stub = get_inference_stub()

        for model_name, model_info in self.models.items():
            if not model_info['active']:
                continue

            try:
                prediction = infer(
                    inference_stub,
                    model_name,
                    frame,
                    metadata=(('protocol', 'gRPC'), ('session_id', '12345'))
                )
                results[model_name] = prediction
            except Exception as e:
                logger.error(f"Inference failed for model {model_name}: {str(e)}")

        return {
            'skill_id': self.skill_id,
            'detections': results,
            'status': 'success'
        }

    async def validate(self) -> bool:
        """验证技能配置"""
        return all(
            model.get('mar_path') and model.get('name')
            for model in self.config.get('models', [])
        )

    def is_model_in_use(self, model_name: str) -> bool:
        """检查模型是否正在被使用"""
        return bool(self.model_tasks.get(model_name))

    def get_model_tasks(self, model_name: str) -> set:
        """获取使用某个模型的所有任务"""
        return self.model_tasks.get(model_name, set())