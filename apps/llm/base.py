from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import time
from dotenv import load_dotenv
from utils.logger_manager import get_logger
from django.conf import settings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from .callbacks import LoggingCallbackHandler

# 加载.env文件中的环境变量
load_dotenv()

class BaseLLMService(ABC):
    """LLM服务基类"""
    
    @abstractmethod
    def invoke(self, messages: List[BaseMessage]) -> Any:
        """调用LLM服务"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """将LLM服务实例转换为可序列化的字典
        
        Returns:
            包含所有必要配置的字典
        """
        return {
            'class_path': f"{self.__class__.__module__}.{self.__class__.__name__}",
            'config': {
                key: getattr(self, key)
                for key in ['api_base', 'api_key', 'model', 'temperature', 'max_tokens']
                if hasattr(self, key)
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseLLMService':
        """从字典创建LLM服务实例
        
        Args:
            data: 包含类路径和配置的字典
            
        Returns:
            LLM服务实例
        """
        from importlib import import_module
        
        # 动态导入模型类
        module_path, class_name = data['class_path'].rsplit('.', 1)
        module = import_module(module_path)
        ModelClass = getattr(module, class_name)
        
        # 创建实例
        return ModelClass(**data['config'])

class LLMServiceFactory:
    """大模型服务工厂"""
    
    @staticmethod
    def create(provider: str, **config) -> BaseChatModel:
        """创建LLM服务实例"""
        logger = get_logger(__class__.__name__)
        logger.info(f"创建LLM服务: provider={provider}")
        
        # 获取LLM配置
        llm_config = getattr(settings, 'LLM_PROVIDERS', {})
        default_provider = llm_config.get('default_provider', 'deepseek')
        providers = {k: v for k, v in llm_config.items() if k != 'default_provider'}
        
        # 检查提供商是否存在
        if provider not in providers:
            logger.warning(f"不支持的LLM提供商: {provider}，使用默认提供商: {default_provider}")
            provider = default_provider
        
        # 获取提供商配置
        provider_config = providers.get(provider, {})
        
        # 获取API密钥
        api_key = config.get('api_key') or os.getenv(f"{provider.upper()}_API_KEY")
        if api_key:
            provider_config['api_key'] = api_key
        
        # 创建回调处理器
        callbacks = [LoggingCallbackHandler()]
        
        # 合并配置
        merged_config = {
            **provider_config,
            **config,
            'callbacks': callbacks,
            'verbose': True  # 启用详细日志
        }
        
        # 根据提供商创建相应的服务实例
        if provider.lower() == "deepseek":
            # 延迟导入，避免循环依赖
            from .deepseek import DeepSeekChatModel
            return DeepSeekChatModel(**merged_config)
        elif provider.lower() == "qwen":
            # 延迟导入，避免循环依赖
            from .qwen import QwenChatModel
            return QwenChatModel(**merged_config)
        elif provider.lower() == "openai":
            from langchain_community.chat_models import ChatOpenAI
            return ChatOpenAI(**merged_config)
        else:
            logger.error(f"未实现的LLM提供商: {provider}")
            raise NotImplementedError(f"LLM provider {provider} is not implemented") 