from typing import Dict, Any, List, Optional
import json
from langchain.schema import SystemMessage, HumanMessage
from ..llm.base import BaseChatModel
from ..knowledge.service import KnowledgeService
from .prompts import TestCaseGeneratorPrompt
from utils.logger_manager import get_logger

class TestCaseGeneratorAgent:
    """测试用例生成Agent"""
    
    def __init__(self, llm_service: BaseChatModel, knowledge_service: KnowledgeService):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.prompt = TestCaseGeneratorPrompt()
        self.logger = get_logger('agent')  # 添加logger
    
    def generate(self, input_text: str, input_type: str = "requirement") -> List[Dict[str, Any]]:
        """生成测试用例"""
        # 确定输入类型描述
        input_type_desc = "需求描述" if input_type == "requirement" else "代码片段"
        
        # 获取知识上下文
        knowledge_context = self._get_knowledge_context(input_text)
        
        # 构建消息
        messages = [
            SystemMessage(content=self.prompt.system_template),
            HumanMessage(content=self.prompt.human_template.format(
                input_type=input_type_desc,
                input_text=input_text,
                knowledge_context=knowledge_context
            ))
        ]
        
        # 调用LLM服务
        try:
            response = self.llm_service(messages)
            result = response.content
            
            # 解析JSON结果
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                json_str = result.split("```")[1].split("```")[0].strip()
            else:
                json_str = result
                
            test_cases = json.loads(json_str)
            self._validate_test_cases(test_cases)
            return test_cases
            
        except Exception as e:
            raise ValueError(f"无法解析生成的测试用例: {str(e)}\n原始响应: {result}")
    
    def _get_knowledge_context(self, input_text: str) -> str:
        """获取相关知识上下文"""
        try:
            # 暂时返回空字符串，直到KnowledgeService实现完成
            return ""
            # knowledge = self.knowledge_service.search_relevant_knowledge(input_text)
            # if knowledge:
            #     return f"\n相关知识：\n{knowledge}"
        except Exception as e:
            self.logger.warning(f"获取知识上下文失败: {str(e)}")
        return ""
    
    def _validate_test_cases(self, test_cases: List[Dict[str, Any]]):
        """验证测试用例格式"""
        for i, test_case in enumerate(test_cases):
            # 检查必要字段
            if "description" not in test_case:
                raise ValueError(f"测试用例 #{i+1} 缺少描述字段")
            
            if "test_steps" not in test_case:
                raise ValueError(f"测试用例 #{i+1} 缺少测试步骤字段")
            
            if "expected_results" not in test_case:
                raise ValueError(f"测试用例 #{i+1} 缺少预期结果字段")
            
            # 检查测试步骤和预期结果的数量是否一致
            if len(test_case["test_steps"]) != len(test_case["expected_results"]):
                raise ValueError(
                    f"测试用例 #{i+1} 的测试步骤数量 ({len(test_case['test_steps'])}) "
                    f"与预期结果数量 ({len(test_case['expected_results'])}) 不一致"
                )