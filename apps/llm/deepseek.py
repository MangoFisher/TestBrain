from typing import Any, List, Optional, Dict
from langchain_core.messages import BaseMessage
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_community.chat_models import ChatOpenAI
from .base import BaseLLMService
import os

class DeepSeekChatModel(ChatOpenAI, BaseLLMService):
    """DeepSeek聊天模型"""
    
    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = "deepseek-chat",
        **kwargs
    ):
        # 设置默认的API基础URL
        api_base = api_base or "https://api.deepseek.com/v1"
        
        # 获取API密钥
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "DeepSeek API key is required. Set it via DEEPSEEK_API_KEY environment variable "
                "or pass it directly."
            )
        
        # 设置为OpenAI格式的API密钥
        os.environ["OPENAI_API_KEY"] = api_key
        
        super().__init__(
            model_name=model,
            openai_api_base=api_base,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """将LLM服务实例转换为可序列化的字典"""
        return {
            'class_path': f"{self.__class__.__module__}.{self.__class__.__name__}",
            'config': {
                'api_base': self.openai_api_base,
                'api_key': self.openai_api_key,
                'model': self.model_name,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeepSeekChatModel':
        """从字典创建实例"""
        return cls(**data['config'])