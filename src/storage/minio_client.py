from minio import Minio
from minio.error import S3Error
from datetime import datetime, timedelta
import io
import cv2
import numpy as np
from typing import Optional, List, Dict
from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class MinioStorage:
    def __init__(self):
        self.config = Config()
        minio_config = self.config.storage['minio']
        
        self.client = Minio(
            endpoint=minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config.get('secure', True)
        )
        
        # 确保存储桶存在
        self.ensure_buckets()

    def ensure_buckets(self):
        """确保所需的存储桶存在"""
        buckets = {
            'video': self.config.storage['minio']['video_bucket'],
            'image': self.config.storage['minio']['image_bucket']
        }
        
        for bucket_name in buckets.values():
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info(f"Created bucket: {bucket_name}")
            except S3Error as e:
                logger.error(f"Error ensuring bucket {bucket_name}: {str(e)}")
                raise

    async def save_video_clip(
        self,
        video_data: bytes,
        task_id: str,
        detection_info: Dict,
        start_time: float,
        end_time: float
    ) -> str:
        """
        保存异常视频片段
        Args:
            video_data: 视频数据
            task_id: 任务ID
            detection_info: 检测信息
            start_time: 开始时间
            end_time: 结束时间
        Returns:
            存储的对象URL
        """
        try:
            # 生成对象名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{task_id}/{timestamp}_{start_time:.2f}_{end_time:.2f}.mp4"
            
            # 准备元数据
            metadata = {
                "task_id": task_id,
                "start_time": str(start_time),
                "end_time": str(end_time),
                "detection_type": detection_info.get("class_name", "unknown"),
                "confidence": str(detection_info.get("confidence", 0))
            }
            
            # 上传视频
            self.client.put_object(
                bucket_name=self.config.storage['minio']['video_bucket'],
                object_name=object_name,
                data=io.BytesIO(video_data),
                length=len(video_data),
                metadata=metadata,
                content_type='video/mp4'
            )
            
            logger.info(f"Saved video clip: {object_name}")
            return self.get_object_url('video', object_name)
            
        except S3Error as e:
            logger.error(f"Error saving video clip: {str(e)}")
            raise

    async def save_detection_image(
        self,
        image: np.ndarray,
        task_id: str,
        detection_info: Dict,
        timestamp: float
    ) -> str:
        """
        保存检测图片
        Args:
            image: OpenCV格式的图片
            task_id: 任务ID
            detection_info: 检测信息
            timestamp: 时间戳
        Returns:
            存储的对象URL
        """
        try:
            # 编码图片
            _, buffer = cv2.imencode('.jpg', image)
            image_data = buffer.tobytes()
            
            # 生成对象名
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            object_name = f"{task_id}/{current_time}_{timestamp:.2f}.jpg"
            
            # 准备元数据
            metadata = {
                "task_id": task_id,
                "timestamp": str(timestamp),
                "detection_type": detection_info.get("class_name", "unknown"),
                "confidence": str(detection_info.get("confidence", 0))
            }
            
            # 上传图片
            self.client.put_object(
                bucket_name=self.config.storage['minio']['image_bucket'],
                object_name=object_name,
                data=io.BytesIO(image_data),
                length=len(image_data),
                metadata=metadata,
                content_type='image/jpeg'
            )
            
            logger.info(f"Saved detection image: {object_name}")
            return self.get_object_url('image', object_name)
            
        except S3Error as e:
            logger.error(f"Error saving detection image: {str(e)}")
            raise

    def get_object_url(
        self,
        bucket_type: str,
        object_name: str,
        expires: int = 7 * 24 * 3600
    ) -> str:
        """
        获取对象的预签名URL
        Args:
            bucket_type: 'video' 或 'image'
            object_name: 对象名称
            expires: URL有效期（秒）
        Returns:
            预签名URL
        """
        try:
            bucket_name = self.config.storage['minio'][f'{bucket_type}_bucket']
            return self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=expires
            )
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise

    async def list_detections(
        self,
        task_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        detection_type: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        列出检测结果
        Args:
            task_id: 任务ID
            start_time: 开始时间
            end_time: 结束时间
            detection_type: 检测类型
        Returns:
            检测结果列表
        """
        try:
            results = {
                'videos': [],
                'images': []
            }
            
            # 遍历视频和图片桶
            for bucket_type in ['video', 'image']:
                bucket_name = self.config.storage['minio'][f'{bucket_type}_bucket']
                prefix = f"{task_id}/"
                
                objects = self.client.list_objects(bucket_name, prefix=prefix)
                for obj in objects:
                    # 获取对象元数据
                    metadata = self.client.stat_object(
                        bucket_name,
                        obj.object_name
                    ).metadata
                    
                    # 检查时间范围
                    obj_time = datetime.strptime(
                        metadata.get('timestamp', ''),
                        '%Y-%m-%d %H:%M:%S'
                    )
                    if start_time and obj_time < start_time:
                        continue
                    if end_time and obj_time > end_time:
                        continue
                        
                    # 检查检测类型
                    if detection_type and metadata.get('detection_type') != detection_type:
                        continue
                        
                    # 添加到结果
                    results[f'{bucket_type}s'].append({
                        'url': self.get_object_url(bucket_type, obj.object_name),
                        'metadata': metadata
                    })
            
            return results
            
        except S3Error as e:
            logger.error(f"Error listing detections: {str(e)}")
            raise 