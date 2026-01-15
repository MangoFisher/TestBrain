from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import time
from dotenv import load_dotenv
from apps.utils.logger_manager import get_logger
from django.conf import settings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from .callbacks import LoggingCallbackHandler
from .deepseek import DeepSeekChatModel
from .qwen import QwenChatModel


# 加载.env文件中的环境变量
load_dotenv()

class BaseLLMService(BaseChatModel):
    """基础LLM服务类"""
    
    def __init__(self):
        # 使用统一日志管理器获取日志记录器
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本响应"""
        pass
    
    @abstractmethod
    def generate_with_history(self, 
                             messages: List[Dict[str, str]], 
                             **kwargs) -> str:
        """基于对话历史生成响应"""
        pass
    
    def _log_request(self, method_name: str, prompt_or_messages, **kwargs):
        """记录请求日志"""
        if isinstance(prompt_or_messages, str):
            # 对于单个prompt，只记录前100个字符
            prompt_preview = prompt_or_messages[:100] + "..." if len(prompt_or_messages) > 100 else prompt_or_messages
            self.logger.info(f"开始调用 {method_name}: prompt='{prompt_preview}'")
        else:
            # 对于消息列表，记录消息数量和最后一条消息
            last_msg = prompt_or_messages[-1] if prompt_or_messages else {}
            last_content = last_msg.get('content', '')
            content_preview = last_content[:100] + "..." if len(last_content) > 100 else last_content
            self.logger.info(f"开始调用 {method_name}: 消息数量={len(prompt_or_messages)}, 最后消息='{content_preview}'")
        
        # 记录关键参数
        important_params = {k: v for k, v in kwargs.items() if k in ['model', 'temperature', 'max_tokens']}
        if important_params:
            self.logger.info(f"调用参数: {important_params}")
    
    def _log_response(self, method_name: str, response: str, elapsed_time: float):
        """记录响应日志"""
        response_preview = response[:100] + "..." if len(response) > 100 else response
        self.logger.info(f"调用成功 {method_name}: 耗时={elapsed_time:.2f}秒, 响应='{response_preview}'")
    
    def _log_error(self, method_name: str, error: Exception, elapsed_time: float):
        """记录错误日志"""
        self.logger.error(f"调用失败 {method_name}: 耗时={elapsed_time:.2f}秒, 错误={str(error)}", exc_info=True)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """实现 BaseChatModel 要求的方法"""
        raise NotImplementedError()
    
    @property
    def _llm_type(self) -> str:
        """返回LLM类型"""
        return "base_llm_service"

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
            from .deepseek import DeepSeekChatModel
            return DeepSeekChatModel(**merged_config)
        elif provider.lower() == "qwen":
            from .qwen import QwenChatModel
            return QwenChatModel(**merged_config)
        elif provider.lower() == "openai":
            from langchain_community.chat_models import ChatOpenAI
            return ChatOpenAI(**merged_config)
        else:
            logger.error(f"未实现的LLM提供商: {provider}")
            raise NotImplementedError(f"LLM provider {provider} is not implemented") 