# 空文件，使llm成为一个Python包 

# 从base模块导出LLMServiceFactory
from langchain_core.language_models.chat_models import BaseChatModel
from .base import LLMServiceFactory

# 导出所有需要在包级别访问的类和函数
__all__ = ['LLMServiceFactory', 'BaseChatModel'] 