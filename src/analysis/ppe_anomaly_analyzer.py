from typing import List, Dict, Any
from src.analysis.base_anomaly_analyzer import BaseAnomalyAnalyzer

class PPEAnomalyAnalyzer(BaseAnomalyAnalyzer):
    def __init__(self):
        self.detections_buffer = {}

    def add_detection(self, task_id: str, detections: List[Dict[str, Any]], timestamp: float) -> None:
        if task_id not in self.detections_buffer:
            self.detections_buffer[task_id] = []
        self.detections_buffer[task_id].append({
            'detections': detections,
            'timestamp': timestamp
        })

    def check_anomalies(self, task_id: str) -> List[Dict[str, Any]]:
        anomalies = []
        recent_detections = self.detections_buffer.get(task_id, [])[-10:]

        # 劳保用品特定的异常检测逻辑
        for d in recent_detections:
            person_count = sum(1 for det in d['detections'] if det['class'] == 'person')
            ppe_violations = self._check_ppe_violations(d['detections'])

            if ppe_violations:
                anomalies.extend(ppe_violations)

        return anomalies

    def get_statistics(self, task_id: str) -> Dict[str, Any]:
        # 劳保用品检测的特定统计
        return {
            'total_detections': len(self.detections_buffer.get(task_id, [])),
            'violation_types': self._get_violation_types(task_id)
        }

    def _check_ppe_violations(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检查劳保用品违规情况"""
        violations = []

        for detection in detections:
            if detection['class'] != 'person':
                continue

            # 初始化违规项
            ppe_status = {
                'helmet': False,
                'vest': False,
                'gloves': False
            }

            # 检查关联对象
            if 'related_objects' in detection:
                for obj in detection['related_objects']:
                    if obj['confidence'] > 0.5:  # 使用置信度阈值
                        if obj['class'] == 'helmet':
                            ppe_status['helmet'] = True
                        elif obj['class'] == 'vest':
                            ppe_status['vest'] = True
                        elif obj['class'] == 'gloves':
                            ppe_status['gloves'] = True

            # 记录违规项
            violation_items = []
            if not ppe_status['helmet']:
                violation_items.append('安全帽')
            if not ppe_status['vest']:
                violation_items.append('反光衣')
            if not ppe_status['gloves']:
                violation_items.append('手套')

            if violation_items:
                violations.append({
                    'type': 'ppe_violation',
                    'severity': 'high' if len(violation_items) > 1 else 'medium',
                    'description': f"未穿戴: {', '.join(violation_items)}",
                    'person_id': detection.get('id', ''),
                    'bbox': detection.get('bbox', []),
                    'missing_items': violation_items
                })

        return violations

    def _get_violation_types(self, task_id: str) -> Dict[str, int]:
        """获取违规类型统计"""
        violation_counts = {
            'helmet': 0,
            'vest': 0,
            'gloves': 0
        }

        if task_id not in self.detections_buffer:
            return violation_counts

        for detection_frame in self.detections_buffer[task_id]:
            violations = self._check_ppe_violations(detection_frame['detections'])
            for violation in violations:
                for item in violation['missing_items']:
                    if '安全帽' in item:
                        violation_counts['helmet'] += 1
                    elif '反光衣' in item:
                        violation_counts['vest'] += 1
                    elif '手套' in item:
                        violation_counts['gloves'] += 1

        return violation_counts
    def is_anomaly(self, detection: Dict[str, Any]) -> bool:
        """判断是否为劳保用品异常"""
        if detection['class'] != 'person':
            return False

        # 获取各个模型的配置
        ppe_config = self.config.skills['ppe_detection']['models']
        thresholds = {
            model['name']: float(model['parameters']['confidence_threshold'])
            for model in ppe_config
        }

        # 检查所需的劳保用品
        required_ppe = {
            'helmet': False,
            'vest': False,
            'gloves': False
        }

        if 'related_objects' in detection:
            for obj in detection['related_objects']:
                threshold = thresholds.get(f"{obj['class']}_detection")
                if threshold and obj['confidence'] > threshold:
                    required_ppe[obj['class']] = True

        # 如果缺少任何一项劳保用品，就判定为异常
        return not all(required_ppe.values())