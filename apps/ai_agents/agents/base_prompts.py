from pathlib import Path
import yaml
import json
from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class PromptTemplateManager:
    """提示词模板管理器"""
    
    def __init__(self):
        """初始化，加载配置文件"""
        config_path = Path(__file__).parent / "prompts_config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def get_test_case_generator_prompt(self) -> ChatPromptTemplate:
        """获取测试用例生成的提示词模板"""
        config = self.config['test_case_generator']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'test_methods': ', '.join(config['test_methods']),
            'test_types': ', '.join(config['test_types'])
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])

    def get_test_case_reviewer_prompt(self) -> ChatPromptTemplate:
        """获取测试用例评审的提示词模板"""
        config = self.config['test_case_reviewer']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'evaluation_aspects': ', '.join(config['evaluation_aspects'])
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 准备人类消息的变量
        human_vars = {
            'review_points': '\n'.join(f"- {point}" for point in config['review_points'])
        }
        
        # 创建人类消息模板 - 不要在这里格式化 test_case
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])
        
    def get_prd_analyser_prompt(self) -> ChatPromptTemplate:
        """获取PRD分析的提示词模板"""
        config = self.config['prd_analyser']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'analysis_focus': ', '.join(config['analysis_focus'])
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])
    
    def get_api_test_case_generator_prompt(self) -> ChatPromptTemplate:
        """获取API测试用例生成的提示词模板"""
        config = self.config['api_test_case_generator']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'api_analysis_focus': ', '.join(config['api_analysis_focus']),
            'template_understanding': '\n'.join(config['template_understanding']),
            'case_count': '{case_count}'
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])
