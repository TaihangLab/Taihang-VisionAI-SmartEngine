class BaseError(Exception):
    """基础异常类"""
    pass

class ConfigError(BaseError):
    """配置相关错误"""
    pass

class VideoProcessError(BaseError):
    """视频处理相关错误"""
    pass

class ModelError(BaseError):
    """模型相关错误"""
    pass

class StorageError(BaseError):
    """存储相关错误"""
    pass

class AuthenticationError(BaseError):
    """认证相关错误"""
    pass

class RateLimitError(BaseError):
    """限流相关错误"""
    pass

class TaskError(BaseError):
    """任务处理相关错误"""
    pass

class SkillError(BaseError):
    """技能相关错误"""
    pass

class MessageError(BaseError):
    """消息队列相关错误"""
    pass 