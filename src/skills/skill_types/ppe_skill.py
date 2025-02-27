from typing import Dict, Any
from src.skills.skill_types.base_skill import BaseSkill
from protos.ts_scripts.torchserve_grpc_client import get_inference_stub, infer
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class PPESkill(BaseSkill):
    """劳保用品检测技能"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        frame = input_data.get('frame')
        task_id = input_data.get('task_id')
        
        if not frame:
            raise ValueError("No frame provided")
            
        # 确保任务已注册
        if not any(task_id in tasks for tasks in self.model_tasks.values()):
            await self.add_task(task_id)
            
        results = {}
        inference_stub = get_inference_stub()
        
        # 执行多个模型（安全帽、反光衣等）
        for model_name, model_info in self.models.items():
            if not model_info['active']:
                continue
                
            try:
                prediction = await infer(
                    inference_stub,
                    model_name,
                    frame,
                    metadata=(('protocol', 'gRPC'), ('task_id', task_id))
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
        if not self.config.get('models'):
            return False
            
        required_params = ['name', 'mar_path', 'type']
        return all(
            all(param in model for param in required_params)
            for model in self.config.get('models', [])
        ) 