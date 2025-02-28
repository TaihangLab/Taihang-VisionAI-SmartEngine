from typing import Dict, Any
import asyncio

from src.analysis.anomaly_analyzer_factory import AnomalyAnalyzerFactory
from src.core.config import Config
from src.skills.skill_orchestrator import SkillOrchestrator
from src.core.task_queue_manager import TaskQueueManager, TaskPriority

from src.messaging.producer import RocketMQProducer
from src.utils.video import VideoProcessor
from src.utils.logger import setup_logger
from src.storage.minio_client import MinioStorage
from src.utils.video_buffer import VideoBuffer

from protos.ts_scripts import task_pb2, task_pb2_grpc

logger = setup_logger(__name__)


class TaskProcessor:
    def __init__(self):
        self.config = Config()
        self.skill_orchestrator = SkillOrchestrator()
        self.producer = RocketMQProducer()
        self.video_processor = VideoProcessor()
        self.storage = MinioStorage()
        self.video_buffer = VideoBuffer()
        self.analyzers = {}
        self.task_manager = TaskQueueManager()
        self._running = True

    async def start(self):
        """启动处理器"""
        await self.producer.start()
        # 启动任务管理器的资源监控
        asyncio.create_task(self.task_manager.adjust_concurrent_tasks())
        # 启动任务处理循环
        asyncio.create_task(self._process_task_queue())
        logger.info("Task processor started successfully")

    async def process_task(self, task_id: str, request: task_pb2.StartTaskRequest):
        """将任务添加到队列"""
        try:
            # 估算任务资源需求
            resource_requirements = self._estimate_resource_requirements(request)
            
            # 根据请求参数确定优先级
            priority = self._determine_task_priority(request)
            
            # 添加到任务队列
            await self.task_manager.add_task(
                task_id=task_id,
                priority=priority,
                resource_requirements=resource_requirements
            )
            
        except Exception as e:
            logger.error(f"Error adding task {task_id} to queue: {str(e)}")
            await self.producer.send_message({
                'task_id': task_id,
                'error': str(e),
                'timestamp': self.video_processor.get_current_timestamp()
            })

    def _estimate_resource_requirements(self, request: task_pb2.StartTaskRequest) -> Dict[str, float]:
        """估算任务资源需求"""
        # 这里可以根据实际情况进行更复杂的估算
        return {
            'cpu': 1.0,  # CPU核心数
            'memory': 2.0,  # GB
            'gpu': 1.0 if request.use_gpu else 0.0  # GPU显存
        }

    def _determine_task_priority(self, request: task_pb2.StartTaskRequest) -> TaskPriority:
        """确定任务优先级"""
        if hasattr(request, 'priority') and request.priority == 'high':
            return TaskPriority.HIGH
        elif hasattr(request, 'priority') and request.priority == 'low':
            return TaskPriority.LOW
        return TaskPriority.MEDIUM

    async def _process_task_queue(self):
        """处理任务队列的主循环"""
        while self._running:
            try:
                # 获取下一个要执行的任务
                task_info = await self.task_manager.get_next_task()
                if task_info is None:
                    await asyncio.sleep(1)
                    continue

                # 处理视频流
                async for frame in self.video_processor.process_stream(
                        task_info.video_stream,
                        frame_rate=task_info.frame_rate,
                        duration=task_info.duration
                ):
                    result = await self._process_frame(
                        task_info.task_id,
                        frame,
                        task_info.skill_name,
                        task_info.alert_level,
                        task_info.roi
                    )

                    if result:
                        await self.producer.send_message(
                            result,
                            tags=task_info.skill_name,
                            keys=task_info.task_id
                        )

                # 标记任务完成
                self.task_manager.complete_task(task_info.task_id)

            except Exception as e:
                logger.error(f"Error processing task from queue: {str(e)}")
                if task_info:
                    self.task_manager.fail_task(task_info.task_id, str(e))
                await asyncio.sleep(1)

    async def _process_frame(self, task_id, frame, skill_name, alert_level, roi):
        """处理单帧"""
        # 执行AI技能
        result = await self.skill_orchestrator.execute_skill(
            skill_name,
            {
                'frame': frame,
                'task_id': task_id,
                'roi': roi
            }
        )

        if not result.get('detections'):
            return None

        result.update({
            'task_id': task_id,
            'alert_level': alert_level,
            'timestamp': self.video_processor.get_current_timestamp()
        })

        # 获取分析器
        if skill_name not in self.analyzers:
            self.analyzers[skill_name] = (
                AnomalyAnalyzerFactory.create_analyzer(skill_name)
            )

        return await self._handle_detections(
            task_id,
            frame,
            result,
            self.analyzers[skill_name],
            skill_name
        )

    async def _handle_detections(self, task_id, frame, result, analyzer, skill_name):
        """处理检测结果"""
        self.video_buffer.add_frame(frame, self.video_processor.get_current_timestamp())
        analyzer.add_detection(
            task_id,
            result['detections'],
            self.video_processor.get_current_timestamp()
        )

        anomalies = analyzer.check_anomalies(task_id)
        if anomalies:
            video_data, start_time, end_time = self.video_buffer.get_clip()
            video_url = await self.storage.save_video_clip(
                video_data, task_id, {'anomalies': anomalies},
                start_time, end_time
            )
            image_url = await self.storage.save_detection_image(
                frame, task_id, {'anomalies': anomalies},
                self.video_processor.get_current_timestamp()
            )

            result.update({
                'anomalies': anomalies,
                'video_url': video_url,
                'image_url': image_url,
                'statistics': analyzer.get_statistics(task_id)
            })

        return result

    async def stop_task(self, task_id: str):
        """停止指定任务"""
        # 标记任务失败
        self.task_manager.fail_task(task_id, "Task stopped by user")
        logger.info(f"Task {task_id} stopped")

    async def stop(self):
        """停止处理器"""
        self._running = False
        await self.producer.stop()
        logger.info("Task processor stopped successfully")