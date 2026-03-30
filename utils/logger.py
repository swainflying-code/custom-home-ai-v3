"""
日志管理模块
提供统一的应用日志记录功能
"""

import logging
import sys
from datetime import datetime
from typing import Optional
import os


def setup_logger(name: str = "custom_home_ai", level: str = "INFO", log_to_file: bool = False) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: 是否输出到文件
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    
    # 如果已经配置过处理器，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # 创建格式器
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_to_file:
        # 创建日志目录
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # 日志文件名
        log_file = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称，如果为None则使用默认名称
    
    Returns:
        logging.Logger: 日志记录器
    """
    if name is None:
        name = "custom_home_ai"
    
    logger = logging.getLogger(name)
    
    # 如果没有处理器，先设置
    if not logger.handlers:
        setup_logger(name)
    
    return logger


class LoggerMixin:
    """日志混入类，为类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取日志记录器"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


# 便捷函数
debug = lambda msg, *args, **kwargs: get_logger().debug(msg, *args, **kwargs)
info = lambda msg, *args, **kwargs: get_logger().info(msg, *args, **kwargs)
warning = lambda msg, *args, **kwargs: get_logger().warning(msg, *args, **kwargs)
error = lambda msg, *args, **kwargs: get_logger().error(msg, *args, **kwargs)
critical = lambda msg, *args, **kwargs: get_logger().critical(msg, *args, **kwargs)
exception = lambda msg, *args, **kwargs: get_logger().exception(msg, *args, **kwargs)
