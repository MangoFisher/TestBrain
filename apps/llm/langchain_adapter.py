from typing import Dict, Any, List, Optional
import os
import time
import json
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage
)
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts.chat import ChatPromptTemplate

from .base import BaseLLMService
from utils.logger_manager import get_logger

class LangChainCallbackHandler(BaseCallbackHandler):
    """LangChain回调处理器，用于记录日志"""
    
    def __init__(self, logger):
        self.logger = logger
        self.start_time = None
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        self.start_time = time.time()
        self.logger.info(f"开始LLM调用: {prompts[:100]}...")
    
    def on_llm_end(self, response, **kwargs):
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        self.logger.info(f"LLM调用完成，耗时: {elapsed_time:.2f}秒")
        self.logger.debug(f"LLM响应: {response}")
    
    def on_llm_error(self, error, **kwargs):
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        self.logger.error(f"LLM调用出错，耗时: {elapsed_time:.2f}秒, 错误: {error}")


class LangChainAdapter(BaseLLMService):
    """LangChain适配器，用于与大模型交互"""
    
    def __init__(self, model: str = None, api_key: str = None, api_base: str = None, **kwargs):
        super().__init__()
        
        # 设置API密钥和基础URL
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        self.model = model or "gpt-3.5-turbo"
        
        # 创建回调处理器
        self.callback_handler = LangChainCallbackHandler(self.logger)
        
        # 创建LangChain聊天模型
        self.chat = ChatOpenAI(
            model_name=self.model,
            openai_api_key=self.api_key,
            openai_api_base=self.api_base,
            temperature=0.7,
            callbacks=[self.callback_handler]
        )
        
        self.logger.info(f"初始化LangChainAdapter: model={self.model}, api_base={self.api_base}")
    
    def generate(self, prompt: str) -> str:
        """生成文本（兼容旧接口）"""
        try:
            start_time = time.time()
            self.logger.info(f"开始生成文本: {prompt[:100]}...")
            
            # 使用简单的消息列表
            messages = [
                SystemMessage(content="你是一个有用的AI助手。"),
                HumanMessage(content=prompt)
            ]
            
            # 调用LangChain聊天模型
            response = self.chat(messages)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"文本生成完成，耗时: {elapsed_time:.2f}秒")
            
            return response.content
        except Exception as e:
            elapsed_time = time.time() - start_time
            self._log_error("generate", e, elapsed_time)
            raise
    
    def generate_with_prompt_template(self, prompt_template: ChatPromptTemplate, **kwargs) -> str:
        """使用提示模板生成文本"""
        try:
            start_time = time.time()
            self.logger.info(f"开始使用提示模板生成文本，参数: {kwargs}")
            
            # 使用提示模板格式化消息
            messages = prompt_template.format_messages(**kwargs)
            
            # 调用LangChain聊天模型
            response = self.chat(messages)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"文本生成完成，耗时: {elapsed_time:.2f}秒")
            
            return response.content
        except Exception as e:
            elapsed_time = time.time() - start_time
            self._log_error("generate_with_prompt_template", e, elapsed_time)
            raise
    
    def _log_error(self, method_name: str, error: Exception, elapsed_time: float):
        """记录错误日志"""
        self.logger.error(
            f"{method_name}方法出错，耗时: {elapsed_time:.2f}秒, "
            f"错误类型: {type(error).__name__}, 错误信息: {str(error)}",
            exc_info=True
        ) 