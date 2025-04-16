from typing import Dict, Any, List
import json
import logging

from ..llm.base import BaseLLMService
from ..knowledge.service import KnowledgeService 
from ..core.models import TestCase
from .prompts import TestCaseReviewerPrompt
from langchain_core.messages import SystemMessage, HumanMessage
from utils.logger_manager import get_logger
from .tasks import llm_invoke



class TestCaseReviewerAgent:
    """测试用例评审Agent"""
    
    def __init__(self, llm_service: BaseLLMService, knowledge_service: KnowledgeService):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.prompt = TestCaseReviewerPrompt()
        self.logger = get_logger(self.__class__.__name__)  # 添加logger

    
    def review(self, test_case: TestCase) -> Dict[str, Any]:
        """评审测试用例"""
        try:
            self.logger.info(f"待评审的测试用例数据为: \n{test_case}")
             # 构造测试用例数据字典
            test_case_dict = {
                "description": test_case.description,
                "test_steps": test_case.test_steps,
                "expected_results": test_case.expected_results
            }
            
            # 使用新的 format_messages 方法获取消息列表
            messages = self.prompt.format_messages(test_case_dict)
            
            self.logger.info(f"构建后的评审提示词: \n{'='*50}\n{messages}\n{'='*50}")
            
            # 使用LangChain的序列化方法
            messages_dicts = [msg.dict() for msg in messages]
            
            # 序列化LLM服务实例
            llm_service_dict = self.llm_service.to_dict()
            self.logger.info("LLM服务实例序列化成功")
            
            # 异步调用LLM服务
            result = llm_invoke.delay(
                llm_service_dict=llm_service_dict,
                messages=messages_dicts
            ).get()
            
            if not result:
                raise ValueError("LLM服务返回空响应")
            
            return result
            
        except Exception as e:
            self.logger.error(f"评审过程出错: {str(e)}", exc_info=True)
            raise Exception(f"评审失败: {str(e)}")

    def _format_prompt(self, test_case):
        """格式化提示词"""
        try:
            prompt = f"""请评审以下测试用例：
            测试用例描述：
            {test_case.description}
            测试步骤：
            {test_case.test_steps}
            预期结果：
            {test_case.expected_results}
            """
            return prompt.strip()
            
        except Exception as e:
            self.logger.error(f"格式化提示词时出错: {str(e)}", exc_info=True)
            raise Exception(f"格式化提示词失败: {str(e)}")
