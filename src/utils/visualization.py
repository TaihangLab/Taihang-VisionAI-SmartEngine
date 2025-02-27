import cv2
import numpy as np
from typing import List, Dict, Tuple

class Visualizer:
    def __init__(self):
        # 为不同类别设置不同的颜色
        self.colors = {
            'person': (0, 255, 0),     # 绿色
            'helmet': (255, 0, 0),     # 蓝色
            'vest': (0, 0, 255),       # 红色
            'flame': (0, 165, 255),    # 橙色
            'default': (255, 255, 0)   # 青色
        }

    def draw_detections(
        self,
        image: np.ndarray,
        detections: List[Dict],
        draw_label: bool = True,
        thickness: int = 2
    ) -> np.ndarray:
        """
        在图像上绘制检测结果
        Args:
            image: 输入图像
            detections: 检测结果列表
            draw_label: 是否绘制标签
            thickness: 线条粗细
        Returns:
            绘制了检测结果的图像
        """
        for det in detections:
            # 获取边界框坐标
            bbox = det['bbox']  # [x, y, width, height]
            x1, y1 = int(bbox[0]), int(bbox[1])
            x2, y2 = int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])
            
            # 获取类别和置信度
            class_name = det['class_name']
            confidence = det['confidence']
            
            # 获取颜色
            color = self.colors.get(class_name, self.colors['default'])
            
            # 绘制边界框
            cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
            
            # 绘制标签
            if draw_label:
                label = f'{class_name} {confidence:.2f}'
                font_scale = 0.6
                font_thickness = 1
                
                # 获取文本大小
                (label_width, label_height), baseline = cv2.getTextSize(
                    label,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    font_thickness
                )
                
                # 绘制标签背景
                cv2.rectangle(
                    image,
                    (x1, y1 - label_height - baseline),
                    (x1 + label_width, y1),
                    color,
                    -1
                )
                
                # 绘制标签文本
                cv2.putText(
                    image,
                    label,
                    (x1, y1 - baseline),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale,
                    (255, 255, 255),
                    font_thickness
                )
        
        return image

    def add_timestamp(
        self,
        image: np.ndarray,
        timestamp: float,
        position: Tuple[int, int] = (10, 30)
    ) -> np.ndarray:
        """
        在图像上添加时间戳
        Args:
            image: 输入图像
            timestamp: 时间戳（秒）
            position: 文本位置
        Returns:
            添加了时间戳的图像
        """
        text = f"Time: {timestamp:.2f}s"
        cv2.putText(
            image,
            text,
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        return image 