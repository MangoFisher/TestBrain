from typing import Dict, Any, List
import json

from ..llm.base import BaseLLMService
from ..llm.langchain_adapter import LangChainAdapter
from ..knowledge.service import KnowledgeService
from ..core.models import TestCase
from .prompts import TestCaseReviewerPrompt

class TestCaseReviewerAgent:
    """测试用例评审Agent"""
    
    def __init__(self, llm_service: BaseLLMService, knowledge_service: KnowledgeService):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.prompt = TestCaseReviewerPrompt()
    
    def review(self, test_case: TestCase) -> Dict[str, Any]:
        """评审测试用例"""
        # 准备需求和代码部分
        requirements_section = ""
        if hasattr(test_case, 'requirements') and test_case.requirements:
            requirements_section = f"需求描述:\n{test_case.requirements}"
            
        code_section = ""
        if hasattr(test_case, 'code_snippet') and test_case.code_snippet:
            code_section = f"代码片段:\n{test_case.code_snippet}"
        
        # 从知识库获取相关知识
        query = f"{test_case.title} {test_case.description}"
        if hasattr(test_case, 'requirements') and test_case.requirements:
            query += f" {test_case.requirements}"
            
        knowledge_results = self.knowledge_service.search_knowledge(query)
        knowledge_context = "\n\n".join([
            f"标题: {item['title']}\n内容: {item['content']}"
            for item in knowledge_results
        ])
        
        if not knowledge_context:
            knowledge_context = "没有找到相关知识。"
        
        # 准备提示模板参数
        prompt_args = {
            "title": test_case.title,
            "description": test_case.description,
            "test_steps": test_case.test_steps,
            "expected_results": test_case.expected_results,
            "requirements_section": requirements_section,
            "code_section": code_section,
            "knowledge_context": knowledge_context
        }
        
        # 获取提示模板
        chat_prompt = self.prompt.get_chat_prompt()
        
        # 调用LLM服务
        if isinstance(self.llm_service, LangChainAdapter):
            # 如果是LangChain适配器，使用提示模板
            result = self.llm_service.generate_with_prompt_template(chat_prompt, **prompt_args)
        else:
            # 如果是其他服务，使用传统方式
            formatted_prompt = f"""你是一位专业的软件测试评审专家，请对以下测试用例进行全面评审。

测试用例信息:
标题: {test_case.title}
描述: {test_case.description}
测试步骤: 
{test_case.test_steps}

预期结果: 
{test_case.expected_results}

{requirements_section}
{code_section}

相关知识库内容:
{knowledge_context}

请对测试用例进行全面评审，包括以下方面：
1. 测试用例是否完整、清晰
2. 测试步骤是否详细、可执行
3. 预期结果是否明确、可验证
4. 是否覆盖了所有功能点和边界条件
5. 是否考虑了异常情况
6. 是否符合测试最佳实践

请以JSON格式返回评审结果，格式如下：
```json
{{
  "score": 评分(1-10),
  "strengths": ["优点1", "优点2", ...],
  "weaknesses": ["缺点1", "缺点2", ...],
  "suggestions": ["改进建议1", "改进建议2", ...],
  "missing_scenarios": ["缺失场景1", "缺失场景2", ...],
  "recommendation": "通过/不通过",
  "comments": "总体评价"
}}
```"""
            result = self.llm_service.generate(formatted_prompt)
        
        # 解析JSON结果
        try:
            # 尝试提取JSON部分
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                json_str = result.split("```")[1].split("```")[0].strip()
            else:
                json_str = result
                
            review_result = json.loads(json_str)
            return review_result
        except Exception as e:
            # 如果解析失败，返回错误信息
            raise ValueError(f"无法解析评审结果: {str(e)}\n原始响应: {result}") 