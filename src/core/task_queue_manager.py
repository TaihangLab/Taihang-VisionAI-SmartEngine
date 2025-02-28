import asyncio
from typing import Dict, Any, Optional
import psutil
import logging
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2

@dataclass
class TaskInfo:
    task_id: str
    priority: TaskPriority
    created_at: datetime
    resource_requirements: Dict[str, float]  # CPU, Memory, GPU requirements
    status: str = "pending"
    
class TaskQueueManager:
    def __init__(self, 
                 max_concurrent_tasks: int = 10,
                 cpu_threshold: float = 80.0,  # CPU使用率阈值
                 memory_threshold: float = 80.0,  # 内存使用率阈值
                 gpu_threshold: float = 80.0):  # GPU使用率阈值
        self.max_concurrent_tasks = max_concurrent_tasks
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.gpu_threshold = gpu_threshold
        
        self.task_queue = asyncio.PriorityQueue()
        self.active_tasks: Dict[str, TaskInfo] = {}
        self.task_results: Dict[str, Any] = {}
        
    async def add_task(self, task_id: str, priority: TaskPriority, resource_requirements: Dict[str, float]) -> None:
        """添加新任务到队列"""
        task_info = TaskInfo(
            task_id=task_id,
            priority=priority,
            created_at=datetime.now(),
            resource_requirements=resource_requirements
        )
        # 优先级队列项：(优先级数值, 创建时间, 任务信息)
        await self.task_queue.put((priority.value, task_info.created_at.timestamp(), task_info))
        logger.info(f"Task {task_id} added to queue with priority {priority}")
        
    async def get_next_task(self) -> Optional[TaskInfo]:
        """获取下一个要执行的任务"""
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            return None
            
        if not self.check_resource_availability():
            logger.warning("System resources exceeded thresholds")
            return None
            
        if self.task_queue.empty():
            return None
            
        _, _, task_info = await self.task_queue.get()
        self.active_tasks[task_info.task_id] = task_info
        task_info.status = "running"
        return task_info
        
    def check_resource_availability(self) -> bool:
        """检查系统资源是否足够"""
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        if cpu_percent > self.cpu_threshold:
            logger.warning(f"CPU usage too high: {cpu_percent}%")
            return False
            
        if memory_percent > self.memory_threshold:
            logger.warning(f"Memory usage too high: {memory_percent}%")
            return False
            
        # TODO: 添加GPU监控
        return True
        
    def complete_task(self, task_id: str, result: Any = None) -> None:
        """标记任务完成"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks.pop(task_id)
            task_info.status = "completed"
            if result is not None:
                self.task_results[task_id] = result
            logger.info(f"Task {task_id} completed")
            
    def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        if task_id in self.active_tasks:
            task_info = self.active_tasks.pop(task_id)
            task_info.status = "failed"
            self.task_results[task_id] = {"error": error}
            logger.error(f"Task {task_id} failed: {error}")
            
    def get_task_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].status
        if task_id in self.task_results:
            return "completed" if "error" not in self.task_results[task_id] else "failed"
        return None
        
    async def adjust_concurrent_tasks(self) -> None:
        """动态调整最大并发任务数"""
        while True:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            
            if cpu_percent > self.cpu_threshold or memory_percent > self.memory_threshold:
                self.max_concurrent_tasks = max(1, self.max_concurrent_tasks - 1)
                logger.info(f"Reduced max concurrent tasks to {self.max_concurrent_tasks}")
            elif cpu_percent < self.cpu_threshold * 0.7 and memory_percent < self.memory_threshold * 0.7:
                self.max_concurrent_tasks += 1
                logger.info(f"Increased max concurrent tasks to {self.max_concurrent_tasks}")
                
            await asyncio.sleep(60)  # 每分钟检查一次 