from typing import Any, List, Optional, Dict
from langchain_core.messages import BaseMessage
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_community.chat_models import ChatOpenAI
from .base import BaseLLMService
import os

class QwenChatModel(ChatOpenAI, BaseLLMService):
    """通义千问聊天模型"""
    
    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = "qwen-max",
        max_tokens: int = 4096,
        **kwargs
    ):
        # 设置默认的API基础URL
        api_base = api_base or "https://dashscope.aliyuncs.com/api/v1"
        
        # 获取API密钥
        api_key = api_key or os.getenv("QWEN_API_KEY")
        if not api_key:
            raise ValueError(
                "Qwen API key is required. Set it via QWEN_API_KEY environment variable "
                "or pass it directly."
            )
        
        # 验证并限制max_tokens的范围
        if max_tokens > 8192:
            max_tokens = 8192
        elif max_tokens < 1:
            max_tokens = 1
            
        # 设置为OpenAI格式的API密钥
        os.environ["OPENAI_API_KEY"] = api_key
        
        super().__init__(
            model_name=model,
            openai_api_base=api_base,
            max_tokens=max_tokens,
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
    def from_dict(cls, data: Dict[str, Any]) -> 'QwenChatModel':
        """从字典创建实例"""
        return cls(**data['config'])