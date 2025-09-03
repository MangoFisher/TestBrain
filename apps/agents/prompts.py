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
                       case_count: int, test_case_min_template: str) -> list:
        """格式化消息
        
        Args:
            api_info: API接口信息
            priority: 测试用例优先级
            case_count: 生成测试用例数量
            test_case_template: 测试用例结构模板
            
        Returns:
            格式化后的消息列表
        """
        # 生成响应摘要，如果有内容则包含标题，否则为空
        response_summary = self._format_response_summary(api_info)
        response_block = f"## 响应摘要\n{response_summary}" if response_summary else ""
        
        return self.prompt_template.format_messages(
            api_name=api_info.get('name', ''),
            method=api_info.get('method', ''),
            path=api_info.get('path', ''),
            priority=priority,
            case_count=case_count,
            inter_parameters_info=self._format_inter_parameters_info(api_info),
            inter_response_summary=response_block,
            test_case_min_template=test_case_min_template
        )
    
    def _format_inter_parameters_info(self, api_info: Dict[str, Any]) -> str:
        """格式化参数的关键信息"""
        request = api_info.get('request', {})
        
        # 提取参数信息
        params_info = []
        
        # 从 query 参数
        for param in request.get('query', []):
            params_info.append({
                'name': param.get('key'),
                'type': param.get('paramType'),
                'required': param.get('required'),
                'sample': param.get('value'),
                'minimum': param.get('minimum', None),
                'maximum': param.get('maximum', None),
                'minLength': param.get('minLength', None),
                'maxLength': param.get('maxLength'),
                'location': 'query'
            })
        
        # 从 rest 参数
        for param in request.get('rest', []):
            params_info.append({
                'name': param.get('key'),
                'type': param.get('paramType'),
                'required': param.get('required'),
                'sample': param.get('value'),
                'minimum': param.get('minimum', None),
                'maximum': param.get('maximum', None),
                'minLength': param.get('minLength', None),
                'maxLength': param.get('maxLength', None),
                'location': 'path'
            })
        
        # 从 body 参数
        body = request.get('body', {})
        if body.get('bodyType') == 'JSON':
            json_body = body.get('jsonBody', {})
            schema = json_body.get('jsonSchema', {})
            properties = schema.get('properties', {})
            
            # 解析 jsonValue 字符串为字典
            json_value_dict = {}
            json_value_str = json_body.get('jsonValue', '')
            if json_value_str:
                try:
                    json_value_dict = json.loads(json_value_str)
                except json.JSONDecodeError:
                    pass  # 如果解析失败，使用空字典
            
            # 遍历 jsonValue 中的参数（参数个数和样本值来源）
            for prop_name, sample_value in json_value_dict.items():
                # 从 jsonSchema.properties 中获取类型信息
                prop_info = properties.get(prop_name, {})
                
                params_info.append({
                    'name': prop_name,
                    'type': prop_info.get('type'),
                    'required': prop_info.get('required'),
                    'sample': sample_value,
                    'minimum': prop_info.get('minimum'),
                    'maximum': prop_info.get('maximum'),
                    'minLength': prop_info.get('minLength'),
                    'maxLength': prop_info.get('maxLength'),
                    'location': 'body'
                })
        
        result = ""
        if params_info:
            result += "\n"
            for param in params_info:
                if param['name']:  # 过滤空参数名
                    result += f"- {param['name']} ({param['location']}): {param['type']}"
                    if param['required']:
                        result += " [必填]"
                    if param['sample']:
                        result += f" 样例: {param['sample']}"
                    if param['minimum'] is not None or param['maximum'] is not None:
                        result += f" 范围: {param['minimum']}-{param['maximum']}"
                    if param['minLength'] is not None or param['maxLength'] is not None:
                        result += f" 长度: {param['minLength']}-{param['maxLength']}"
                    result += "\n"
        else:
            result += "无参数\n"
        
        return result
    
    def _format_response_summary(self, api_info: Dict[str, Any]) -> str:
        """格式化响应摘要信息"""
        #TODO: 目前暂不将接口响应信息传入大模型, 后面有需要再补充
        return ""
        response = api_info.get('response', [])
        
        if not response:
            return "响应: 无响应信息"
        
        # 只提取关键信息
        result = "响应摘要:\n"
        for resp in response:
            status_code = resp.get('statusCode', '')
            default_flag = resp.get('defaultFlag', False)
            result += f"- 状态码: {status_code} {'(默认)' if default_flag else ''}\n"
            
            # 只提取响应体的关键字段信息
            body = resp.get('body', {})
            if body.get('bodyType') == 'JSON':
                json_body = body.get('jsonBody', {})
                if json_body.get('jsonValue'):
                    # 只显示关键字段
                    json_value = json_body['jsonValue']
                    if isinstance(json_value, dict):
                        key_fields = ['code', 'message', 'data', 'success']
                        for field in key_fields:
                            if field in json_value:
                                result += f"  {field}: {json_value[field]}\n"
                elif json_body.get('jsonSchema'):
                    # 只显示必填字段
                    required_fields = json_body.get('jsonSchema', {}).get('required', [])
                    if required_fields:
                        result += f"  必填字段: {', '.join(required_fields)}\n"
        
        return result
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
