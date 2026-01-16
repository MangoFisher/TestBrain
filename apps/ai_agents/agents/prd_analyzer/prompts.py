from pathlib import Path
import yaml
from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from ..base_prompts import BasePromptManager


class PrdAnalyserPromptManager(BasePromptManager):
    """PRD分析提示词管理器"""
    
    def __init__(self, config_path: str):
        """初始化，加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
    
    def get_prd_analyser_prompt(self) -> ChatPromptTemplate:
        """获取PRD分析的提示词模板"""
        config = self.config
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'analysis_focus': ', '.join(config['analysis_focus'])
        }
        
        # 创建系统消息模板
        system_template_formatted = config['system_template'].format(**system_vars)
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template_formatted)
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(config['human_template'])
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])


class PrdAnalyserPrompt:
    """PRD分析提示词"""
    
    def __init__(self):
        # 获取当前文件所在目录的configs子目录下的配置文件
        config_path = Path(__file__).parent / "configs" / "prompt_config.yaml"
        # 初始化具体的提示词模板管理器
        self.prompt_manager = PrdAnalyserPromptManager(str(config_path))
        self.prompt_template = self.prompt_manager.get_prd_analyser_prompt()
    
    def format_messages(self, markdown_content: str) -> list:
        """格式化消息
        
        Args:
            markdown_content: Markdown格式的PRD文档内容
            
        Returns:
            格式化后的消息列表
        """
        return self.prompt_template.format_messages(
            markdown_content=markdown_content
        )