import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from django.conf import settings

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class LogManager:
    """统一的日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if LogManager._initialized:
            return
            
        # 从Django设置中获取日志配置，如果不存在则使用默认值
        self.log_level = LOG_LEVELS.get(
            getattr(settings, 'LOG_LEVEL', 'INFO'),
            logging.INFO
        )
        
        self.log_dir = getattr(settings, 'LOG_DIR', 'logs')
        self.max_bytes = getattr(settings, 'LOG_MAX_BYTES', 10 * 1024 * 1024)  # 10MB
        self.backup_count = getattr(settings, 'LOG_BACKUP_COUNT', 5)
        
        # 创建日志目录
        Path(self.log_dir).mkdir(exist_ok=True)
        
        # 配置根日志记录器
        self._configure_root_logger()
        
        # 创建各个模块的日志记录器
        self.loggers = {
            'core': self._get_logger('core'),
            'llm': self._get_logger('llm'),
            'agents': self._get_logger('agents'),
            'knowledge': self._get_logger('knowledge'),
            'api': self._get_logger('api'),
        }
        
        LogManager._initialized = True
        
    def _configure_root_logger(self):
        """配置根日志记录器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [thread=%(thread)d %(threadName)s] - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # 添加文件处理器 - 所有日志
        all_log_file = os.path.join(self.log_dir, 'all.log')
        file_handler = logging.handlers.RotatingFileHandler(
            all_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [thread=%(thread)d %(threadName)s] - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # 添加文件处理器 - 仅错误日志
        error_log_file = os.path.join(self.log_dir, 'error.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
    
    def _get_logger(self, name):
        """获取指定名称的日志记录器"""
        logger = logging.getLogger(name)
        
        # 为特定模块创建日志文件
        log_file = os.path.join(self.log_dir, f'{name}.log')
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        handler.setLevel(self.log_level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [thread=%(thread)d %(threadName)s] - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # 清除现有处理器
        for h in logger.handlers[:]:
            logger.removeHandler(h)
            
        logger.addHandler(handler)
        return logger
    
    def get_logger(self, name):
        """获取日志记录器"""
        if name in self.loggers:
            return self.loggers[name]
        
        # 处理子模块日志记录器，如llm.deepseek
        for module, logger in self.loggers.items():
            if name.startswith(f"{module}."):
                return logging.getLogger(name)
        
        # 如果不是预定义的模块，返回根据名称创建的日志记录器
        return logging.getLogger(name)

# 创建单例实例
log_manager = LogManager()

def get_logger(name):
    """获取日志记录器的便捷函数"""
    return log_manager.get_logger(name)
