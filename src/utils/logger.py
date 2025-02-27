import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from src.core.config import Config

def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（可选）
        level: 日志级别（可选）
    Returns:
        配置好的日志记录器
    """
    config = Config()
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = (level or config.logging['level']).upper()
    logger.setLevel(getattr(logging, log_level))
    
    # 创建格式化器
    formatter = logging.Formatter(
        config.logging['format'],
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file or config.logging.get('file'):
        log_path = Path(log_file or config.logging['file'])
        
        # 确保日志目录存在
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建循环文件处理器
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class LoggerMixin:
    """
    日志记录器混入类
    为类提供日志记录功能
    """
    @property
    def logger(self) -> logging.Logger:
        if not hasattr(self, '_logger'):
            self._logger = setup_logger(self.__class__.__name__)
        return self._logger


def log_exception(logger: logging.Logger):
    """
    异常日志装饰器
    记录函数执行期间的异常
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise
        return wrapper
    return decorator 