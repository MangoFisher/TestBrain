from ..base_prompts import PromptTemplateManager

class TestCaseGeneratorPrompt:
    """测试用例生成提示词"""
    
    def __init__(self):
        self.prompt_manager = PromptTemplateManager()
        self.prompt_template = self.prompt_manager.get_test_case_generator_prompt()
    
    def format_messages(self, requirements: str, case_design_methods: str = "", 
                       case_categories: str = "", knowledge_context: str = "",case_count: int = 10) -> list:
        """格式化消息
        
        Args:
            requirements: 需求描述
            case_design_methods: 测试用例设计方法
            case_categories: 测试用例类型
            knowledge_context: 知识库上下文
            case_count: 生成用例条数
        Returns:
            格式化后的消息列表
        """
        # 处理空值情况
        if not case_design_methods:
            case_design_methods = "所有适用的测试用例设计方法"
        
        if not case_categories:
            case_categories = "所有适用的测试类型"
            
        # 格式化知识上下文提示
        knowledge_prompt = (
            f"参考以下知识库内容：\n{knowledge_context}"
            if knowledge_context
            else "根据你的专业知识"
        )
        
        return self.prompt_template.format_messages(
            requirements=requirements,
            case_design_methods=case_design_methods,
            case_categories=case_categories,
            case_count=case_count,
            knowledge_context=knowledge_prompt
        )