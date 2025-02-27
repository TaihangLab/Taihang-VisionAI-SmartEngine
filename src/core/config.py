import os
import yaml
from typing import Dict, Any

class Config:
    """配置管理类"""
    
    def __init__(self):
        self._config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'configs',
            'default.yaml'
        )
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @property
    def server(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self._config.get('server', {})
    
    @property
    def skills(self) -> Dict[str, Dict[str, Any]]:
        """获取技能配置"""
        return self._config.get('skills', {})
        
    @property
    def rate_limit(self) -> Dict[str, Any]:
        """获取限流配置"""
        return self._config.get('rate_limit', {})

    def __getattr__(self, name: str) -> Any:
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"Config has no attribute '{name}'") 