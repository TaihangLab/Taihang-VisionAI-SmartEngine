import numpy as np
from typing import List, Tuple, Dict
import cv2

class ROIProcessor:
    @staticmethod
    def create_mask(
        image_shape: Tuple[int, int],
        points: List[Tuple[int, int]]
    ) -> np.ndarray:
        """
        创建ROI掩码
        Args:
            image_shape: 图像形状 (height, width)
            points: ROI多边形的顶点列表
        Returns:
            掩码数组
        """
        mask = np.zeros(image_shape[:2], dtype=np.uint8)
        if points:
            points_array = np.array([points], dtype=np.int32)
            cv2.fillPoly(mask, points_array, 255)
        return mask

    @staticmethod
    def filter_detections(
        detections: List[Dict],
        roi_mask: np.ndarray
    ) -> List[Dict]:
        """
        过滤ROI区域外的检测结果
        Args:
            detections: 检测结果列表
            roi_mask: ROI掩码
        Returns:
            过滤后的检测结果列表
        """
        filtered_detections = []
        
        for det in detections:
            bbox = det['bbox']  # [x, y, width, height]
            # 计算边界框中心点
            center_x = int(bbox[0] + bbox[2] / 2)
            center_y = int(bbox[1] + bbox[3] / 2)
            
            # 检查中心点是否在ROI内
            if roi_mask[center_y, center_x] > 0:
                filtered_detections.append(det)
                
        return filtered_detections

    @staticmethod
    def draw_roi(
        image: np.ndarray,
        points: List[Tuple[int, int]],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        在图像上绘制ROI区域
        Args:
            image: 输入图像
            points: ROI多边形的顶点列表
            color: 线条颜色 (B,G,R)
            thickness: 线条粗细
        Returns:
            绘制了ROI的图像
        """
        if points:
            points_array = np.array([points], dtype=np.int32)
            cv2.polylines(
                image,
                points_array,
                True,
                color,
                thickness
            )
        return image 