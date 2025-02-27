from typing import Dict, Any
import asyncio

from src.analysis.anomaly_analyzer_factory import AnomalyAnalyzerFactory
from src.core.config import Config
from src.skills.skill_orchestrator import SkillOrchestrator
from src.core.task_scheduler import TaskScheduler, TaskPriority
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
        self.scheduler = TaskScheduler(
            max_concurrent_tasks=self.config.get('task_processor.max_concurrent_tasks', 10),
            max_memory_percent=self.config.get('task_processor.max_memory_percent', 80.0),
            max_cpu_percent=self.config.get('task_processor.max_cpu_percent', 80.0)
        )
        self._running = True

    async def start(self):
        """启动处理器"""
        await self.producer.start()
        await self.scheduler.initialize()
        asyncio.create_task(self._process_task_queue())
        logger.info("Task processor started successfully")

    async def _process_task_queue(self):
        """处理任务队列的主循环"""
        while self._running:
            try:
                task_id = await self.scheduler.get_next_task()
                if task_id and task_id in self._tasks:
                    request = self._tasks[task_id]
                    asyncio.create_task(self._process_single_task(task_id, request))
                await asyncio.sleep(0.1)  # 避免过度占用CPU
            except Exception as e:
                logger.error(f"Error in task queue processing: {e}")
                await asyncio.sleep(1)

    async def process_task(self, task_id: str, request: task_pb2.StartTaskRequest):
        """添加任务到队列"""
        priority = TaskPriority.HIGH if request.priority == 'high' else \
                  TaskPriority.LOW if request.priority == 'low' else \
                  TaskPriority.MEDIUM
                  
        if await self.scheduler.add_task(task_id, priority):
            self._tasks[task_id] = request
            return True
        return False

    async def _process_single_task(self, task_id: str, request: task_pb2.StartTaskRequest):
        """处理单个任务"""
        try:
            # 处理视频流
            async for frame in self.video_processor.process_stream(
                    request.video_stream,
                    frame_rate=request.frame_rate,
                    duration=request.duration
            ):
                if not self._running or not await self.scheduler.get_task_status(task_id) == 'running':
                    break

                result = await self._process_frame(
                    task_id,
                    frame,
                    request.skill_name,
                    request.alert_level,
                    request.roi
                )

                if result:
                    await self.producer.send_message(
                        result,
                        tags=request.skill_name,
                        keys=task_id
                    )

            await self.scheduler.complete_task(task_id, success=True)

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            await self.scheduler.complete_task(task_id, success=False)
            await self.producer.send_message({
                'task_id': task_id,
                'error': str(e),
                'timestamp': self.video_processor.get_current_timestamp()
            })

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
        await self.scheduler.complete_task(task_id, success=False)

    async def stop(self):
        """停止处理器"""
        self._running = False
        await self.scheduler.cleanup()
        await self.producer.stop()
        logger.info("Task processor stopped successfully")