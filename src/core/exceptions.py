class AIEngineError(Exception):
    """基础异常类"""
    pass

class ModelError(AIEngineError):
    """模型相关错误"""
    pass

class SkillError(AIEngineError):
    """技能相关错误"""
    pass

class ConfigError(AIEngineError):
    """配置相关错误"""
    pass

class MessageError(AIEngineError):
    """消息队列相关错误"""
    pass 