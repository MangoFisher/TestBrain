"""
Java代码分析AI Agent的提示词管理器。
"""
import os
from typing import Dict, Any
from pathlib import Path

from apps.ai_agents.common.base_prompts import BasePromptManager


class JavaCodeAnalyzerPromptManager(BasePromptManager):
    """Java代码分析AI Agent的提示词管理器"""
    
    def __init__(self):
        # 调用父类构造函数
        super().__init__()
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        # 由于基类不处理配置加载，这里直接返回硬编码的提示词
        # 或者您可以实现一个简单的配置加载机制
        import yaml
        
        current_dir = Path(__file__).parent
        config_path = current_dir / "configs" / "prompt_config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        return config.get("java_code_analyzer_system_prompt", "")
    
    def get_user_prompt(self, repo_path: str, base_commit: str, new_commit: str) -> str:
        """获取用户提示词"""
        return f"""请分析以下两个 commit 之间的变更影响，并给出测试建议：

项目路径: {repo_path}
基准 commit: {base_commit}
新 commit: {new_commit}

请自主决策调用合适的工具进行深入分析，最后生成相应的测试用例。
"""