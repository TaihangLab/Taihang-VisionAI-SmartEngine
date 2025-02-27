from typing import List, Dict, Any
from src.analysis.base_anomaly_analyzer import BaseAnomalyAnalyzer

class HelmetAnomalyAnalyzer(BaseAnomalyAnalyzer):
    def __init__(self):
        self.detections_buffer = {}  # 存储检测结果的缓冲区

    def add_detection(self, task_id: str, detections: List[Dict[str, Any]], timestamp: float) -> None:
        if task_id not in self.detections_buffer:
            self.detections_buffer[task_id] = []
        self.detections_buffer[task_id].append({
            'detections': detections,
            'timestamp': timestamp
        })

    def check_anomalies(self, task_id: str) -> List[Dict[str, Any]]:
        anomalies = []
        recent_detections = self.detections_buffer.get(task_id, [])[-10:]  # 分析最近10帧

        # 安全帽特定的异常检测逻辑
        no_helmet_count = sum(
            1 for d in recent_detections
            for det in d['detections']
            if det['class'] == 'person' and not self._has_helmet(det)
        )

        if no_helmet_count >= 5:  # 如果连续5帧检测到未戴安全帽
            anomalies.append({
                'type': 'no_helmet',
                'severity': 'high',
                'description': '检测到工人未佩戴安全帽'
            })

        return anomalies

    def get_statistics(self, task_id: str) -> Dict[str, Any]:
        # 安全帽检测的特定统计
        return {
            'total_detections': len(self.detections_buffer.get(task_id, [])),
            'violation_rate': self._calculate_violation_rate(task_id)
        }

    def _has_helmet(self, detection: Dict[str, Any]) -> bool:
        """检查人员是否戴安全帽"""
        if detection['class'] != 'person':
            return False

        # 检查关联的头部区域是否有安全帽
        if 'related_objects' in detection:
            for obj in detection['related_objects']:
                if obj['class'] == 'helmet' and obj['confidence'] > 0.5:
                    return True
        return False

    def _calculate_violation_rate(self, task_id: str) -> float:
        """计算违规率"""
        if task_id not in self.detections_buffer:
            return 0.0

        total_persons = 0
        total_violations = 0

        for detection_frame in self.detections_buffer[task_id]:
            for detection in detection_frame['detections']:
                if detection['class'] == 'person':
                    total_persons += 1
                    if not self._has_helmet(detection):
                        total_violations += 1

        return round(total_violations / total_persons, 3) if total_persons > 0 else 0.0

    def is_anomaly(self, detection: Dict[str, Any]) -> bool:
        """判断是否为安全帽异常"""
        if detection['class'] != 'person':
            return False

        # 从配置文件获取阈值
        confidence_threshold = self.config.skills['helmet_detection']['models'][0]['parameters']['confidence_threshold']

        # 检查是否有高置信度的安全帽
        if 'related_objects' in detection:
            for obj in detection['related_objects']:
                if (obj['class'] == 'helmet' and
                        obj['confidence'] > float(confidence_threshold)):
                    return False
        return True