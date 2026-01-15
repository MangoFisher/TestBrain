from typing import Dict, Any, List, Optional
import json
from langchain_core.messages import SystemMessage, HumanMessage
from apps.llm.base import BaseLLMService
from apps.knowledge.service import KnowledgeService
from .prompts import TestCaseGeneratorPrompt
from apps.utils.logger_manager import get_logger
import re
class TestCaseGeneratorAgent:
    """测试用例生成Agent"""
    
    def __init__(self, llm_service: BaseLLMService, knowledge_service: KnowledgeService, case_design_methods: List[str], case_categories: List[str], case_count: int = 10):
        self.llm_service = llm_service
        self.case_design_methods = case_design_methods
        self.case_categories = case_categories
        self.case_count = case_count
        self.knowledge_service = knowledge_service
        self.prompt = TestCaseGeneratorPrompt()
        self.logger = get_logger(self.__class__.__name__)  # 添加logger
    
    def generate(self, input_text: str, input_type: str = "requirement") -> List[Dict[str, Any]]:
        """生成测试用例"""
        self.logger.info(f"开始生成测试用例,进入生成测试用例的TestCaseGeneratorAgent")
        # 确定输入类型描述
        input_type_desc = "需求描述" if input_type == "requirement" else "代码片段"
        
        # 获取知识上下文
        knowledge_context = self._get_knowledge_context(input_text)
        self.logger.info(f"获取到知识库上下文: \n{'='*50}\n{knowledge_context}\n{'='*50}")
        
        # 处理设计方法和测试类型
        case_design_methods = ",".join(self.case_design_methods) if self.case_design_methods else ""
        case_categories = ",".join(self.case_categories) if self.case_categories else ""
        
        # 使用新的 format_messages 方法获取消息列表
        messages = self.prompt.format_messages(
            requirements=input_text,
            case_design_methods=case_design_methods,
            case_categories=case_categories,
            case_count=self.case_count,
            knowledge_context=knowledge_context
        )
        self.logger.info(f"构建后大模型提示词+用户需求消息: \n{'='*50}\n{messages}\n{'='*50}")
        
        # 调用LLM服务
        try:
            response = self.llm_service.invoke(messages)
            result = response.content
            self.logger.info(f"LLM原始响应: \n{'='*50}\n{result}\n{'='*50}")
            
            # 尝试提取JSON部分
            json_str = self._extract_json_from_response(result)
            if not json_str:
                raise ValueError("无法从响应中提取有效的JSON数据")
                
            # 尝试解析JSON
            test_cases = json.loads(json_str)
            self.logger.info(f"_validate_test_cases处理前的用例个数: {len(test_cases)}")
            
            valid_test_cases = self._validate_test_cases(test_cases)
            return valid_test_cases
            
        except Exception as e:
            raise ValueError(f"无法解析生成的测试用例: {str(e)}\n原始响应: {result}")
    
    def _get_knowledge_context(self, input_text: str) -> str:
        """获取相关知识上下文"""
        try:
            # 暂时返回空字符串，直到KnowledgeService实现完成
            # return ""
            knowledge = self.knowledge_service.search_relevant_knowledge(input_text)
            if knowledge:
                return f"{knowledge}"
        except Exception as e:
            self.logger.warning(f"获取知识上下文失败: {str(e)}")
        return ""
    
    def _validate_test_cases(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证并修复测试用例格式
        
        Args:
            test_cases: 原始测试用例列表
            
        Returns:
            验证并修复后的测试用例列表
        """  
        valid_test_cases = []
        required_fields = {"description", "test_steps", "expected_results"}
        
        for i, test_case in enumerate(test_cases):
            try:
                # 如果不是字典格式，跳过这个测试用例
                if not isinstance(test_case, dict):
                    self.logger.warning(f"测试用例 #{i+1} 不是字典格式，已跳过")
                    continue
                
                # 检查必要字段是否存在
                missing_fields = required_fields - set(test_case.keys())
                if missing_fields:
                    self.logger.warning(f"测试用例 #{i+1} 缺少必要字段: {missing_fields}，已跳过")
                    continue
                
                # 验证并修复字段格式
                # 1. description必须是字符串
                if not isinstance(test_case['description'], str):
                    self.logger.warning(f"测试用例 #{i+1} 的description不是字符串格式，已跳过")
                    continue
                
                # 2. test_steps必须是列表
                if not isinstance(test_case['test_steps'], list):
                    self.logger.warning(f"测试用例 #{i+1} 的test_steps格式无法修复，已跳过")
                    continue
                
                # 3. expected_results必须是列表
                if not isinstance(test_case['expected_results'], list):
                    self.logger.warning(f"测试用例 #{i+1} 的expected_results格式无法修复，已跳过")
                    continue
                
                # 确保所有字段都不为空
                if not test_case['description'].strip():
                    self.logger.warning(f"测试用例 #{i+1} 的description为空，已跳过")
                    continue
                
                if not test_case['test_steps']:
                    self.logger.warning(f"测试用例 #{i+1} 的test_steps为空，已跳过")
                    continue
                
                if not test_case['expected_results']:
                    self.logger.warning(f"测试用例 #{i+1} 的expected_results为空，已跳过")
                    continue
                # 通过所有验证，添加到有效列表
                valid_test_cases.append(test_case)
                
            except Exception as e:
                self.logger.warning(f"处理测试用例 #{i+1} 时出错: {str(e)}，已跳过")
                continue
        
        if not valid_test_cases:
            raise ValueError("没有找到任何合法的测试用例")
        
        self.logger.info(f"共处理 {len(test_cases)} 个测试用例，"
                        f"其中 {len(valid_test_cases)} 个合法")
        
        return valid_test_cases
            
    def _extract_json_from_response(self, response: str) -> str:
        """从响应中提取JSON部分并进行基础修复
        
        Args:
            response: 原始响应字符串
            
        Returns:
            修复后的JSON字符串
        """
        # 使用正则表达式提取JSON字符串
        result = ""
        right_format_pattern = r'^\[([\s\S]*)\]$'
        match = re.search(right_format_pattern, response)
        if match:
            result = match.group(0)  # 使用group(0)返回完整匹配，包含方括号
        else:
            #从字符串中找到最后一个出现},的位置，然后取},前面的内容,并补全]和json结束标记```
            last_comma_index = response.rfind('},')
            if last_comma_index != -1:
                result = response[:last_comma_index+1] + ']'
        # self.logger.info(f"_extract_json_from_response函数处理结果: \n{'='*50}\n{result}\n{'='*50}")    
        return result
        

            
