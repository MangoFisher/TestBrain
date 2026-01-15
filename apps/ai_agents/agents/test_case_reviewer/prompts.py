from ..base_prompts import PromptTemplateManager
from typing import Dict, Any


class TestCaseReviewerPrompt:
    """测试用例评审提示词"""
    
    def __init__(self):
        self.prompt_manager = PromptTemplateManager()
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
            for point in self.prompt_manager.config['test_case_reviewer']['review_points']
        )
        
        return self.prompt_template.format_messages(
            test_case=test_case_str,
            review_points=review_points
        )