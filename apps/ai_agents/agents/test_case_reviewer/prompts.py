from pathlib import Path
import yaml
from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from ..base_prompts import BasePromptManager


class TestCaseReviewerPromptManager(BasePromptManager):
    """测试用例评审提示词管理器"""
    
    def __init__(self, config_path: str):
        """初始化，加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
    
    def get_test_case_reviewer_prompt(self) -> ChatPromptTemplate:
        """获取测试用例评审的提示词模板"""
        config = self.config
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'evaluation_aspects': ', '.join(config['evaluation_aspects'])
        }
        
        # 创建系统消息模板
        system_template_formatted = config['system_template'].format(**system_vars)
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template_formatted)
        
        # 准备人类消息的变量
        human_vars = {
            'review_points': '\n'.join(f"- {point}" for point in config['review_points'])
        }
        
        # 创建人类消息模板 - 不要在这里格式化 test_case
        human_message_prompt = HumanMessagePromptTemplate.from_template(config['human_template'])
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])


class TestCaseReviewerPrompt:
    """测试用例评审提示词"""
    
    def __init__(self):
        # 获取当前文件所在目录的configs子目录下的配置文件
        config_path = Path(__file__).parent / "configs" / "prompt_config.yaml"
        # 初始化具体的提示词模板管理器
        self.prompt_manager = TestCaseReviewerPromptManager(str(config_path))
        self.prompt_template = self.prompt_manager.get_test_case_reviewer_prompt()
    
    def format_messages(self, test_case: Dict[str, Any]) -> list:
        """格式化消息
        
        Args:
            test_case: 测试用例数据
            
        Returns:
            格式化后的消息列表
        """
        # 格式化测试用例数据为字符串
        test_case_str = (
            f"测试用例描述：\n{test_case.get('description', '')}\n\n"
            f"测试步骤：\n{test_case.get('test_steps', '')}\n\n"
            f"预期结果：\n{test_case.get('expected_results', '')}"
        )
        
        # 获取评审点列表
        review_points = '\n'.join(
            f"- {point}" 
            for point in self.prompt_manager.config['review_points']
        )
        
        return self.prompt_template.format_messages(
            test_case=test_case_str,
            review_points=review_points
        )