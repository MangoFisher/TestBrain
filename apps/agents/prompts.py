from langchain.prompts import PromptTemplate
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

class BasePrompt:
    """提示词基类"""
    @property
    def system_template(self) -> str:
        """系统提示模板"""
        raise NotImplementedError("子类必须实现system_template方法")
    
    @property
    def human_template(self) -> str:
        """人类提示模板"""
        raise NotImplementedError("子类必须实现human_template方法")
    
    def get_chat_prompt(self) -> ChatPromptTemplate:
        """获取聊天提示模板"""
        system_message_prompt = SystemMessagePromptTemplate.from_template(self.system_template)
        human_message_prompt = HumanMessagePromptTemplate.from_template(self.human_template)
        
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])


class TestCaseGeneratorPrompt(BasePrompt):
    """测试用例生成提示词"""
    
    @property
    def system_template(self) -> str:
        return """你是一位专业的软件测试专家，擅长根据需求或代码生成全面的测试用例。
你的测试用例应该全面覆盖功能点、边界条件、异常情况等。
你必须按照指定的格式返回测试用例，包括测试用例描述、测试步骤和预期结果。"""
    
    @property
    def human_template(self) -> str:
        return """请根据以下{input_type}生成全面的测试用例。

{input_type}: 
{input_text}

相关知识库内容:
{knowledge_context}

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


class TestCaseReviewerPrompt(BasePrompt):
    """测试用例评审提示词"""
    
    @property
    def system_template(self) -> str:
        return """你是一位专业的软件测试评审专家，擅长评审测试用例的质量和完整性。
你的评审应该全面考虑测试用例的完整性、清晰度、可执行性、覆盖率等方面。
你必须按照指定的格式返回评审结果。"""
    
    @property
    def human_template(self) -> str:
        return """请对以下测试用例进行全面评审。

测试用例信息:
标题: {title}
描述: {description}
测试步骤: 
{test_steps}

预期结果: 
{expected_results}

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
