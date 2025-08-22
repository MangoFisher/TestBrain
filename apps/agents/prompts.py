from pathlib import Path
import yaml
import json
from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate

class PromptTemplateManager:
    """提示词模板管理器"""
    
    def __init__(self):
        """初始化，加载配置文件"""
        config_path = Path(__file__).parent / "prompts_config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def get_test_case_generator_prompt(self) -> ChatPromptTemplate:
        """获取测试用例生成的提示词模板"""
        config = self.config['test_case_generator']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'test_methods': ', '.join(config['test_methods']),
            'test_types': ', '.join(config['test_types'])
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])

    def get_test_case_reviewer_prompt(self) -> ChatPromptTemplate:
        """获取测试用例评审的提示词模板"""
        config = self.config['test_case_reviewer']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'evaluation_aspects': ', '.join(config['evaluation_aspects'])
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 准备人类消息的变量
        human_vars = {
            'review_points': '\n'.join(f"- {point}" for point in config['review_points'])
        }
        
        # 创建人类消息模板 - 不要在这里格式化 test_case
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])
        
    def get_prd_analyser_prompt(self) -> ChatPromptTemplate:
        """获取PRD分析的提示词模板"""
        config = self.config['prd_analyser']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'analysis_focus': ', '.join(config['analysis_focus'])
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])
    
    def get_api_test_case_generator_prompt(self) -> ChatPromptTemplate:
        """获取API测试用例生成的提示词模板"""
        config = self.config['api_test_case_generator']
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'api_analysis_focus': ', '.join(config['api_analysis_focus']),
            'template_understanding': '\n'.join(config['template_understanding']),
            'case_count': '{case_count}'
        }
        
        # 创建系统消息模板
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            config['system_template'].format(**system_vars)  # 直接格式化模板
        )
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            config['human_template']
        )
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])

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


class APITestCaseGeneratorPrompt:
    """API测试用例生成提示词"""
    
    def __init__(self):
        self.prompt_manager = PromptTemplateManager()
        self.prompt_template = self.prompt_manager.get_api_test_case_generator_prompt()
    
    def format_messages(self, api_info: Dict[str, Any], priority: str, 
                       case_count: int, test_case_template: str) -> list:
        """格式化消息
        
        Args:
            api_info: API接口信息
            priority: 测试用例优先级
            case_count: 生成测试用例数量
            test_case_template: 测试用例结构模板
            
        Returns:
            格式化后的消息列表
        """
        return self.prompt_template.format_messages(
            api_name=api_info.get('name', ''),
            method=api_info.get('method', ''),
            path=api_info.get('path', ''),
            priority=priority,
            case_count=case_count,
            request_structure=self._format_request_structure(api_info),
            response_structure=self._format_response_structure(api_info),
            test_case_template=test_case_template
        )
    
    def _format_request_structure(self, api_info: Dict[str, Any]) -> str:
        """格式化请求结构信息"""
        request = api_info.get('request', {})
        
        # 格式化基本信息
        structure = f"请求方法: {request.get('method', '')}\n"
        structure += f"请求路径: {request.get('path', '')}\n"
        
        # 格式化请求头
        headers = request.get('headers', [])
        if headers:
            structure += "\n请求头:\n"
            for header in headers:
                structure += f"- {header.get('key', '')}: {header.get('value', '')}\n"
        
        # 格式化查询参数
        query = request.get('query', [])
        if query:
            structure += "\n查询参数:\n"
            for param in query:
                structure += f"- {param.get('key', '')}: {param.get('value', '')} ({param.get('paramType', 'string')})\n"
        
        # 格式化请求体
        body = request.get('body', {})
        if body.get('bodyType') == 'JSON':
            json_body = body.get('jsonBody', {})
            if json_body.get('jsonValue'):
                structure += f"\n请求体 (JSON):\n{json_body['jsonValue']}\n"
            elif json_body.get('jsonSchema'):
                structure += f"\n请求体 Schema:\n{json.dumps(json_body['jsonSchema'], ensure_ascii=False, indent=2)}\n"
        
        return structure
    
    def _format_response_structure(self, api_info: Dict[str, Any]) -> str:
        """格式化响应结构信息"""
        response = api_info.get('response', [])
        
        structure = "响应状态码:\n"
        for resp in response:
            status_code = resp.get('statusCode', '')
            default_flag = resp.get('defaultFlag', False)
            structure += f"- {status_code} {'(默认)' if default_flag else ''}\n"
            
            # 格式化响应体
            body = resp.get('body', {})
            if body.get('bodyType') == 'JSON':
                json_body = body.get('jsonBody', {})
                if json_body.get('jsonValue'):
                    structure += f"  响应体: {json_body['jsonValue']}\n"
                elif json_body.get('jsonSchema'):
                    required_fields = json_body.get('jsonSchema', {}).get('required', [])
                    if required_fields:
                        structure += f"  必填字段: {', '.join(required_fields)}\n"
        
        return structure


# 使用示例
if __name__ == "__main__":
    # 测试用例生成
    # generator = TestCaseGeneratorPrompt()
    # messages = generator.format_messages(
    #     requirements="实现用户登录功能",
    #     case_design_methods="等价类划分法",
    #     case_categories="功能测试",
    #     knowledge_context="用户登录需要验证用户名和密码"
    # )
    # print("Generator Messages:", messages)
    
    # # 测试用例评审
    # reviewer = TestCaseReviewerPrompt()
    # test_case = {
    #     "description": "测试用户登录功能",
    #     "test_steps": ["1. 输入用户名", "2. 输入密码", "3. 点击登录按钮"],
    #     "expected_results": ["1. 显示输入框", "2. 密码显示为星号", "3. 登录成功"]
    # }
    # messages = reviewer.format_messages(test_case)
    # print("\nReviewer Messages:", messages)
    
    # PRD分析
    analyser = PrdAnalyserPrompt()
    prd_content = """
    # 用户登录功能
    
    ## 功能描述
    允许用户通过用户名和密码登录系统。
    
    ## 详细需求
    1. 用户需要输入用户名和密码
    2. 系统验证用户名和密码的正确性
    3. 登录成功后跳转到首页
    """
    messages = analyser.format_messages(prd_content)
    print("\nPRD Analyser Messages:", messages)
