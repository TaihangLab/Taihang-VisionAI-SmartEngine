import pytest
from unittest.mock import Mock, patch
from src.skills.skill_orchestrator import SkillOrchestrator
from src.core.exceptions import SkillError

@pytest.mark.asyncio
class TestSkillOrchestrator:
    async def test_create_skill_success(self, skill_orchestrator):
        """测试成功创建技能"""
        skill_config = {
            "name": "test_skill",
            "type": "detection",
            "models": ["model1"],
            "config": {"threshold": 0.5}
        }
        
        skill_name = await skill_orchestrator.create_skill(skill_config)
        assert skill_name == "test_skill"
        assert skill_name in skill_orchestrator.skills

    async def test_create_skill_invalid_config(self, skill_orchestrator):
        """测试创建技能时配置无效"""
        skill_config = {
            "type": "detection"  # 缺少name字段
        }
        
        with pytest.raises(SkillError):
            await skill_orchestrator.create_skill(skill_config)

    async def test_execute_skill(self, skill_orchestrator):
        """测试执行技能"""
        # 创建测试技能
        skill_config = {
            "name": "test_skill",
            "type": "detection",
            "models": ["model1"]
        }
        await skill_orchestrator.create_skill(skill_config)

        # 模拟输入数据
        input_data = {
            "frame": b"test_frame",
            "task_id": "test_task"
        }

        # 执行技能
        result = await skill_orchestrator.execute_skill("test_skill", input_data)
        assert isinstance(result, dict) 