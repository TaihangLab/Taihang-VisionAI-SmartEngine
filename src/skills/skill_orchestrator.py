from typing import Dict, Any
from src.skills.skill_types.base_skill import BaseSkill
from src.skills.skill_types.helmet_skill import HelmetSkill
from src.skills.skill_types.ppe_skill import PPESkill
from src.core.exceptions import SkillError
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class SkillOrchestrator:
    _skill_types = {
        'helmet_detection': HelmetSkill,
        'ppe_detection': PPESkill
    }

    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self.config = Config()
        self._init_skills()

    def _init_skills(self):
        """根据配置初始化技能"""
        for skill_id, skill_config in self.config.skills.items():
            if not skill_config.get('enabled', True):
                continue

            try:
                skill_type = skill_config.get('type')
                if skill_type not in self._skill_types:
                    logger.warning(f"Unsupported skill type: {skill_type}")
                    continue
                    
                skill_class = self._skill_types[skill_type]
                skill = skill_class(skill_id, skill_config)
                self.skills[skill_id] = skill
            except Exception as e:
                logger.error(f"Failed to initialize skill {skill_id}: {str(e)}")

    async def execute_skill(self, skill_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能"""
        if skill_id not in self.skills:
            raise SkillError(f"Skill {skill_id} not found")

        try:
            result = await self.skills[skill_id].execute(input_data)
            return result
        except Exception as e:
            raise SkillError(f"Error executing skill {skill_id}: {str(e)}")

    def get_skill(self, skill_id: str) -> BaseSkill:
        """获取技能实例"""
        if skill_id not in self.skills:
            raise SkillError(f"Skill {skill_id} not found")
        return self.skills[skill_id]

    def list_skills(self) -> Dict[str, Dict]:
        """列出所有技能"""
        return {id: skill.config for id, skill in self.skills.items()}