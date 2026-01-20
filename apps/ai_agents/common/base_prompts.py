"""提示词管理基类"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate


class BasePromptManager:
    """基础提示词管理器 - 仅提供通用方法，不处理配置加载"""
    
    def _create_chat_prompt_template(self, system_template: str, human_template: str) -> ChatPromptTemplate:
        """创建聊天提示词模板"""
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])


class BasePrompt:
    """基础提示词类 - 仅定义接口"""
    
    def format_messages(self, **kwargs):
        """格式化消息 - 子类必须实现"""
        raise NotImplementedError("子类需要实现 format_messages 方法")
