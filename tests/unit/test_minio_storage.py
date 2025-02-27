import pytest
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime
from minio.error import S3Error
from src.storage.minio_client import MinioStorage
from src.core.config import Config

@pytest.fixture
def minio_storage():
    with patch('src.storage.minio_client.Minio') as mock_minio:
        storage = MinioStorage()
        # 模拟Minio客户端
        storage.client = mock_minio.return_value
        yield storage

@pytest.mark.asyncio
class TestMinioStorage:
    async def test_save_video_clip(self, minio_storage):
        """测试保存视频片段"""
        # 准备测试数据
        video_data = b"fake_video_data"
        task_id = "test_task"
        detection_info = {
            "class_name": "flame",
            "confidence": 0.95
        }
        start_time = 10.5
        end_time = 15.5

        # 模拟put_object方法
        minio_storage.client.put_object = Mock()
        
        # 调用保存方法
        url = await minio_storage.save_video_clip(
            video_data,
            task_id,
            detection_info,
            start_time,
            end_time
        )

        # 验证调用
        minio_storage.client.put_object.assert_called_once()
        call_args = minio_storage.client.put_object.call_args[1]
        
        # 验证参数
        assert call_args['bucket_name'] == Config().storage['minio']['video_bucket']
        assert task_id in call_args['object_name']
        assert call_args['length'] == len(video_data)
        assert call_args['content_type'] == 'video/mp4'
        
        # 验证元数据
        metadata = call_args['metadata']
        assert metadata['task_id'] == task_id
        assert metadata['detection_type'] == 'flame'
        assert float(metadata['confidence']) == 0.95
        assert float(metadata['start_time']) == start_time
        assert float(metadata['end_time']) == end_time

    async def test_save_detection_image(self, minio_storage):
        """测试保存检测图片"""
        # 准备测试数据
        image = np.zeros((100, 100, 3), dtype=np.uint8)  # 创建空白图片
        task_id = "test_task"
        detection_info = {
            "class_name": "person",
            "confidence": 0.88
        }
        timestamp = 20.5

        # 模拟put_object方法
        minio_storage.client.put_object = Mock()
        
        # 调用保存方法
        url = await minio_storage.save_detection_image(
            image,
            task_id,
            detection_info,
            timestamp
        )

        # 验证调用
        minio_storage.client.put_object.assert_called_once()
        call_args = minio_storage.client.put_object.call_args[1]
        
        # 验证参数
        assert call_args['bucket_name'] == Config().storage['minio']['image_bucket']
        assert task_id in call_args['object_name']
        assert call_args['content_type'] == 'image/jpeg'
        
        # 验证元数据
        metadata = call_args['metadata']
        assert metadata['task_id'] == task_id
        assert metadata['detection_type'] == 'person'
        assert float(metadata['confidence']) == 0.88
        assert float(metadata['timestamp']) == timestamp

    async def test_list_detections(self, minio_storage):
        """测试列出检测结果"""
        # 准备测试数据
        task_id = "test_task"
        start_time = datetime(2024, 1, 1)
        end_time = datetime(2024, 1, 2)
        detection_type = "flame"

        # 模拟list_objects方法
        mock_object = Mock()
        mock_object.object_name = f"{task_id}/test.mp4"
        minio_storage.client.list_objects = Mock(return_value=[mock_object])

        # 模拟stat_object方法
        mock_stat = Mock()
        mock_stat.metadata = {
            'timestamp': '2024-01-01 12:00:00',
            'detection_type': 'flame',
            'confidence': '0.95'
        }
        minio_storage.client.stat_object = Mock(return_value=mock_stat)

        # 调用列表方法
        results = await minio_storage.list_detections(
            task_id,
            start_time,
            end_time,
            detection_type
        )

        # 验证结果
        assert 'videos' in results
        assert 'images' in results
        assert len(results['videos']) > 0 or len(results['images']) > 0

    def test_ensure_buckets(self, minio_storage):
        """测试确保存储桶存在"""
        # 模拟bucket_exists方法返回False
        minio_storage.client.bucket_exists = Mock(return_value=False)
        minio_storage.client.make_bucket = Mock()

        # 调用方法
        minio_storage.ensure_buckets()

        # 验证调用
        assert minio_storage.client.make_bucket.call_count == 2  # 应该创建两个桶

    async def test_error_handling(self, minio_storage):
        """测试错误处理"""
        # 模拟S3Error
        minio_storage.client.put_object = Mock(side_effect=S3Error("Test error"))

        # 验证是否正确抛出异常
        with pytest.raises(S3Error):
            await minio_storage.save_video_clip(
                b"test",
                "test_task",
                {"class_name": "test", "confidence": 0.9},
                0,
                1
            )

    async def test_get_object_url(self, minio_storage):
        """测试获取对象URL"""
        # 准备测试数据
        object_name = "test_task/test.mp4"
        expected_url = "http://test-url.com"
        
        # 模拟presigned_get_object方法
        minio_storage.client.presigned_get_object = Mock(return_value=expected_url)

        # 获取视频URL
        video_url = minio_storage.get_object_url('video', object_name)
        assert video_url == expected_url

        # 获取图片URL
        image_url = minio_storage.get_object_url('image', object_name)
        assert image_url == expected_url

        # 验证调用参数
        calls = minio_storage.client.presigned_get_object.call_args_list
        assert len(calls) == 2
        assert calls[0][0][1] == object_name  # 验证对象名称
        assert 'expires' in calls[0][1]  # 验证过期时间参数 