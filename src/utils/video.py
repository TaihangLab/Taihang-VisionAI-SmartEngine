import cv2
import numpy as np
from typing import AsyncIterator, List, Tuple, Optional
import asyncio
import time
from src.core.exceptions import VideoProcessError
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class VideoProcessor:
    def __init__(self):
        self._start_time: float = 0
        self._current_frame: int = 0
        self._cap: Optional[cv2.VideoCapture] = None

    async def process_stream(
        self,
        stream_url: str,
        frame_rate: int = 1,
        duration: int = 0,
        resize: Optional[Tuple[int, int]] = None
    ) -> AsyncIterator[np.ndarray]:
        """
        处理视频流
        Args:
            stream_url: RTSP流地址或视频文件路径
            frame_rate: 抽帧频率（每秒处理几帧）
            duration: 处理持续时间（秒），0表示持续处理
            resize: 调整图片大小，格式为(width, height)
        """
        try:
            self._cap = cv2.VideoCapture(stream_url)
            if not self._cap.isOpened():
                raise VideoProcessError(f"Failed to open video stream: {stream_url}")

            self._start_time = time.time()
            self._current_frame = 0
            
            # 计算帧间隔
            original_fps = self._cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(original_fps / frame_rate)
            
            while True:
                # 检查处理时间是否超出限制
                if duration > 0 and (time.time() - self._start_time) > duration:
                    break

                # 读取帧
                ret, frame = await self._read_frame()
                if not ret:
                    break

                # 按照指定频率抽帧
                if self._current_frame % frame_interval == 0:
                    # 调整图片大小
                    if resize:
                        frame = cv2.resize(frame, resize)
                    
                    yield frame

                self._current_frame += 1

        except Exception as e:
            logger.error(f"Error processing video stream: {str(e)}")
            raise VideoProcessError(str(e))
        
        finally:
            await self.release()

    async def _read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """异步读取视频帧"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._cap.read)

    def get_current_timestamp(self) -> float:
        """获取当前帧的时间戳"""
        return time.time() - self._start_time

    async def release(self):
        """释放资源"""
        if self._cap:
            self._cap.release()
            self._cap = None 