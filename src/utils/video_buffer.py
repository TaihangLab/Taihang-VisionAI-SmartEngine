import cv2
import numpy as np
from collections import deque
from typing import List, Optional, Tuple
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class VideoBuffer:
    """视频帧缓冲区，用于保存异常发生前后的视频片段"""
    
    def __init__(self, buffer_size: int = 150):  # 默认5秒(30fps)
        self.buffer_size = buffer_size
        self.frame_buffer = deque(maxlen=buffer_size)
        self.timestamp_buffer = deque(maxlen=buffer_size)
        self.fps = 30  # 默认帧率

    def add_frame(self, frame: np.ndarray, timestamp: float):
        """添加新帧到缓冲区"""
        self.frame_buffer.append(frame.copy())
        self.timestamp_buffer.append(timestamp)

    def get_clip(
        self,
        before_frames: int = 90,  # 3秒
        after_frames: int = 90,   # 3秒
        current_index: Optional[int] = None
    ) -> Tuple[bytes, float, float]:
        """
        获取指定位置前后的视频片段
        Returns:
            (视频数据, 开始时间, 结束时间)
        """
        if not self.frame_buffer:
            raise ValueError("Buffer is empty")

        # 如果未指定位置，使用最新帧的位置
        if current_index is None:
            current_index = len(self.frame_buffer) - 1

        # 计算片段的起止位置
        start_idx = max(0, current_index - before_frames)
        end_idx = min(len(self.frame_buffer), current_index + after_frames)

        # 提取帧
        frames = list(self.frame_buffer)[start_idx:end_idx]
        timestamps = list(self.timestamp_buffer)[start_idx:end_idx]

        # 创建视频写入器
        height, width = frames[0].shape[:2]
        temp_file = f"temp_clip_{timestamps[0]:.2f}_{timestamps[-1]:.2f}.mp4"
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(temp_file, fourcc, self.fps, (width, height))

        try:
            # 写入帧
            for frame in frames:
                writer.write(frame)

            writer.release()

            # 读取视频文件
            with open(temp_file, 'rb') as f:
                video_data = f.read()

            return video_data, timestamps[0], timestamps[-1]

        finally:
            # 清理临时文件
            import os
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def clear(self):
        """清空缓冲区"""
        self.frame_buffer.clear()
        self.timestamp_buffer.clear()

    def get_current_frame(self) -> Optional[np.ndarray]:
        """获取最新帧"""
        return self.frame_buffer[-1].copy() if self.frame_buffer else None

    def get_current_timestamp(self) -> Optional[float]:
        """获取最新帧的时间戳"""
        return self.timestamp_buffer[-1] if self.timestamp_buffer else None 