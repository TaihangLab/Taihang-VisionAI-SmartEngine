import pytest
from unittest.mock import Mock, patch
from src.models.model_service import ModelService
from src.core.exceptions import ModelError

@pytest.mark.asyncio
class TestModelService:
    async def test_load_model_success(self, model_service):
        """测试成功加载模型"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await model_service.load_model(
                "test_model",
                "test_path",
                batch_size=1,
                min_workers=1,
                max_workers=1
            )
            
            assert result is True
            mock_post.assert_called_once()

    async def test_load_model_failure(self, model_service):
        """测试加载模型失败"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = Mock()
            mock_response.status = 500
            mock_response.text = Mock(return_value="Error")
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(ModelError):
                await model_service.load_model(
                    "test_model",
                    "test_path"
                )

    async def test_get_model_status(self, model_service):
        """测试获取模型状态"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = Mock(return_value={"status": "Running"})
            mock_get.return_value.__aenter__.return_value = mock_response

            status = await model_service.get_model_status("test_model")
            assert status["status"] == "Running" 