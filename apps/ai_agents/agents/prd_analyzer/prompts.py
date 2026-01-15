from ..base_prompts import PromptTemplateManager

class PrdAnalyserPrompt:
    """PRD分析提示词"""
    
    def __init__(self):
        self.prompt_manager = PromptTemplateManager()
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