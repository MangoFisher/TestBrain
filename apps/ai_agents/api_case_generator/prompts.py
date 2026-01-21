from pathlib import Path
import yaml
import json
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from apps.ai_agents.common.base_prompts import BasePromptManager


class APITestCaseGeneratorPromptManager(BasePromptManager):
    """API测试用例生成提示词管理器"""
    
    def __init__(self, config_path: str):
        """初始化，加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
    
    def get_api_test_case_generator_prompt(self) -> ChatPromptTemplate:
        """获取API测试用例生成的提示词模板"""
        config = self.config
        
        # 准备系统消息的变量并格式化模板
        system_vars = {
            'role': config['role'],
            'capabilities': config['capabilities'],
            'api_analysis_focus': ', '.join(config['api_analysis_focus']),
            'template_understanding': '\n'.join(config['template_understanding']),
            'case_count': '{case_count}'
        }
        
        # 创建系统消息模板
        system_template_formatted = config['system_template'].format(**system_vars)
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template_formatted)
        
        # 创建人类消息模板
        human_message_prompt = HumanMessagePromptTemplate.from_template(config['human_template'])
        
        # 组合成聊天提示词模板
        return ChatPromptTemplate.from_messages([
            system_message_prompt,
            human_message_prompt
        ])


class APITestCaseGeneratorPrompt:
    """API测试用例生成提示词"""
    
    def __init__(self):
        # 获取当前文件所在目录的configs子目录下的配置文件
        config_path = Path(__file__).parent / "configs" / "prompt_config.yaml"
        # 初始化具体的提示词模板管理器
        self.prompt_manager = APITestCaseGeneratorPromptManager(str(config_path))
        self.prompt_template = self.prompt_manager.get_api_test_case_generator_prompt()
    
    def format_messages(self, api_info: Dict[str, Any], priority: str, 
                       case_count: int, api_test_case_min_template: str, 
                       include_format_instructions: bool = False,
                       case_rule_override: str | None = None) -> list:
        """格式化消息
        
        Args:
            api_info: API接口信息
            priority: 测试用例优先级
            case_count: 生成测试用例数量
            api_test_case_min_template: 测试用例结构模板
            include_format_instructions: 是否包含格式说明（用于重试）
            case_rule_override: 自定义测试用例生成规则（Markdown格式），用于覆盖模板中的默认规则（可选）
            
        Returns:
            格式化后的消息列表
        """
        # 生成响应摘要，如果有内容则包含标题，否则为空
        response_summary = self._format_response_summary(api_info)
        response_block = f"## 响应摘要\n{response_summary}" if response_summary else ""
        
        # 获取基础消息
        messages = self.prompt_template.format_messages(
            api_name=api_info.get('name', ''),
            method=api_info.get('method', ''),
            path=api_info.get('path', ''),
            priority=priority,
            case_count=case_count,
            api_parameters_info=self._format_api_parameters_info(api_info),
            api_response_summary=response_block,
            api_test_case_min_template=api_test_case_min_template
        )

        # 若提供了规则覆盖，将其追加/替换到最后的人类消息中
        if case_rule_override:
            override_text = str(case_rule_override)
            marker = '## 测试用例生成规则'
            for msg in reversed(messages):
                if hasattr(msg, 'content'):
                    content = msg.content
                    if isinstance(content, str):
                        idx = content.find(marker)
                        if idx >= 0:
                            msg.content = content[:idx] + override_text
                        else:
                            msg.content = content + f"\n\n{override_text}"
                    break
        
        # 如果需要格式说明（重试时），追加到最后一个 HumanMessage
        if include_format_instructions:
            # 尝试导入格式说明
            try:
                from .api_test_case_parser import get_format_instructions
                format_instr = get_format_instructions()
                format_extra = f"\n\n重要要求：\n- 只输出 JSON，不要任何解释性文本\n- 严格遵守以下格式说明：\n{format_instr}"
                
                # 找到最后一个 HumanMessage 并追加格式说明
                for msg in reversed(messages):
                    if hasattr(msg, 'content') and hasattr(msg, 'type') and msg.type == 'human':
                        if isinstance(msg.content, str):
                            msg.content += format_extra
                        break
            except ImportError:
                # 如果无法导入格式说明，则跳过这部分
                pass
        
        return messages
    
    def _format_api_parameters_info(self, api_info: Dict[str, Any]) -> str:
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