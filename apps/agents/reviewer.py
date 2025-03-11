from typing import Dict, Any, List
import json
import logging

from ..llm.base import BaseLLMService
from ..llm.langchain_adapter import LangChainAdapter
from ..knowledge.service import KnowledgeService
from ..core.models import TestCase
from .prompts import TestCaseReviewerPrompt
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

class TestCaseReviewerAgent:
    """测试用例评审Agent"""
    
    def __init__(self, llm_service: BaseLLMService, knowledge_service: KnowledgeService):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.prompt = TestCaseReviewerPrompt()
    
    def review(self, test_case: TestCase) -> Dict[str, Any]:
        """评审测试用例"""
        try:
            # 构造提示词
            formatted_prompt = self._format_prompt(test_case)
            
            # 创建消息列表
            messages = [
                SystemMessage(content=(
                    "你是一个专业的测试用例评审专家，请根据以下几个方面评审测试用例：\n"
                    "1. 测试步骤是否清晰、完整\n"
                    "2. 预期结果是否明确、可验证\n"
                    "3. 是否覆盖了主要测试场景\n"
                    "4. 是否存在改进建议"
                )),
                HumanMessage(content=formatted_prompt)
            ]
            
            # 记录消息内容
            logger.info("评审消息详细信息:")
            for msg in messages:
                logger.info(f"消息类型: {type(msg).__name__}")
                logger.info(f"消息内容:\n{msg.content}")
                logger.info("="*50)
            
            # 调用LLM服务
            result = self.llm_service.invoke(messages)  # 使用 invoke 方法替代 chat
            
            # 记录LLM返回结果
            logger.info(f"LLM评审结果:\n"
                       f"{'='*50}\n"
                       f"{result}\n"
                       f"{'='*50}")
            
            return result
            
        except Exception as e:
            logger.error(f"评审过程出错: {str(e)}", exc_info=True)
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
            logger.error(f"格式化提示词时出错: {str(e)}", exc_info=True)
            raise Exception(f"格式化提示词失败: {str(e)}")
