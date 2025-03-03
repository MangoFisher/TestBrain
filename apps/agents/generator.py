from typing import Dict, Any, List, Optional
import json

from ..llm.base import BaseLLMService
from ..llm.langchain_adapter import LangChainAdapter
from ..knowledge.service import KnowledgeService
from .prompts import TestCaseGeneratorPrompt

class TestCaseGeneratorAgent:
    """测试用例生成Agent"""
    
    def __init__(self, llm_service: BaseLLMService, knowledge_service: KnowledgeService):
        self.llm_service = llm_service
        self.knowledge_service = knowledge_service
        self.prompt = TestCaseGeneratorPrompt()
    
    def generate(self, input_text: str, input_type: str = "requirement") -> List[Dict[str, Any]]:
        """生成测试用例"""
        # 确定输入类型描述
        input_type_desc = "需求描述" if input_type == "requirement" else "代码片段"
        
        # 从知识库获取相关知识
        # knowledge_results = self.knowledge_service.search_knowledge(input_text)
        # knowledge_context = "\n\n".join([
        #     f"标题: {item['title']}\n内容: {item['content']}"
        #     for item in knowledge_results
        # ])
        
        # if not knowledge_context:
        #     knowledge_context = "没有找到相关知识。"
        
        # 准备提示模板参数
        prompt_args = {
            "input_type": input_type_desc,
            "input_text": input_text,
            #"knowledge_context": knowledge_context
        }
        
        # 获取提示模板
        chat_prompt = self.prompt.get_chat_prompt()
        
        # 调用LLM服务
        if isinstance(self.llm_service, LangChainAdapter):
            # 如果是LangChain适配器，使用提示模板
            result = self.llm_service.generate_with_prompt_template(chat_prompt, **prompt_args)
        else:
            # 如果是其他服务，使用传统方式
            formatted_prompt = f"""你是一位专业的软件测试专家，请根据以下{input_type_desc}生成全面的测试用例。

{input_type_desc}: 
{input_text}



请生成全面的测试用例，必须包含以下内容：
1. 测试用例描述：简明扼要地描述测试的目的和内容
2. 测试步骤：详细的步骤列表，从1到n编号
3. 预期结果：每个步骤对应的预期结果，从1到n编号

请以JSON格式返回，格式如下：
```json
[
  {{
    "description": "测试用例描述",
    "test_steps": [
      "步骤1",
      "步骤2",
      ...
    ],
    "expected_results": [
      "预期结果1",
      "预期结果2",
      ...
    ]
  }},
  ...
]
```

请确保测试步骤和预期结果的数量一致，并且每个步骤都有对应的预期结果。"""
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
                
            test_cases = json.loads(json_str)
            
            # 验证测试用例格式
            self._validate_test_cases(test_cases)
            
            return test_cases
        except Exception as e:
            # 如果解析失败，返回错误信息
            raise ValueError(f"无法解析生成的测试用例: {str(e)}\n原始响应: {result}")
    
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