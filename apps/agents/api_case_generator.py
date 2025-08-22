import json
import os
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompts import APITestCaseGeneratorPrompt
from ..llm.base import LLMServiceFactory

logger = logging.getLogger(__name__)

class APITestCaseGeneratorAgent:
    """API测试用例生成Agent"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        self.llm_provider = llm_provider
        self.llm = LLMServiceFactory.create(llm_provider)
        self.prompt = APITestCaseGeneratorPrompt()
        self.template = self._load_test_case_template()
        self.max_workers = 5
    
    def _load_test_case_template(self) -> Dict[str, Any]:
        """加载测试用例结构模板"""
        template_path = os.path.join(
            os.path.dirname(__file__),
            'templates',
            'api_test_case_template.jsonc'
        )
        # 优先使用 json5 以支持模板中的注释；若不可用则回退到标准 json
        try:
            import json5  # type: ignore
            with open(template_path, 'r', encoding='utf-8') as f:
                return json5.load(f)
        except Exception as e:
            logger.warning(f"使用 json5 解析模板失败或未安装，回退到标准 JSON 解析: {e}")
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _generate_single_test_case(self, api_info: Dict[str, Any], 
                                  priority: str, case_number: int) -> Optional[Dict[str, Any]]:
        """生成单个测试用例"""
        import threading
        thread_id = threading.current_thread().ident
        
        try:
            # 格式化提示词
            messages = self.prompt.format_messages(
                api_info=api_info,
                priority=priority,
                case_number=case_number,
                test_case_template=json.dumps(self.template, ensure_ascii=False, indent=2)
            )
            # 简单打印提示词内容（调用大模型前）
            try:
                prompt_text = "\n\n".join([getattr(m, 'content', str(m)) for m in messages])
                logger.info(f"[Thread-{thread_id}] [LLM Prompt] API={api_info.get('name', '')} Case={case_number}\n{prompt_text}")
            except Exception as _:
                pass
            
            # 调用大模型（不做兜底重试）
            if hasattr(self.llm, 'generate_with_history'):
                response = self.llm.generate_with_history(messages)
            else:
                from langchain_core.messages import HumanMessage, SystemMessage
                langchain_messages = []
                for msg in messages:
                    if hasattr(msg, 'type') and msg.type == 'system':
                        langchain_messages.append(SystemMessage(content=msg.content))
                    elif hasattr(msg, 'type') and msg.type == 'human':
                        langchain_messages.append(HumanMessage(content=msg.content))
                    elif hasattr(msg, 'role') and msg.role == 'system':
                        langchain_messages.append(SystemMessage(content=msg.content))
                    elif hasattr(msg, 'role') and msg.role == 'user':
                        langchain_messages.append(HumanMessage(content=msg.content))
                    else:
                        langchain_messages.append(msg)
                invoke_result = self.llm.invoke(langchain_messages)
                response = getattr(invoke_result, 'content', invoke_result)
            
            # 解析响应
            test_case = self._parse_response_to_test_case(response)
            if not test_case:
                return None
            
            # 后处理：填充固定值、生成断言等
            test_case = self._post_process_test_case(test_case, api_info, priority)
            
            return test_case
            
        except Exception as e:
            logger.error(f"[Thread-{thread_id}] 生成测试用例失败: {e}")
            return None
    
    def _parse_response_to_test_case(self, response: Any) -> Optional[Dict[str, Any]]:
        """解析大模型响应为测试用例结构"""
        try:
            # 归一化为字符串
            if not isinstance(response, str):
                response = getattr(response, 'content', str(response))
            # 移除可能的markdown标记
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            clean_response = clean_response.strip()
            return json.loads(clean_response)
        except json.JSONDecodeError as e:
            logger.error(f"解析大模型响应失败: {e}")
            return None
    
    def _post_process_test_case(self, test_case: Dict[str, Any], 
                               api_info: Dict[str, Any], priority: str) -> Dict[str, Any]:
        """后处理测试用例：填充固定值、生成断言等"""
        try:
            # 填充基本信息
            test_case['priority'] = priority
            test_case['status'] = 'DONE'
            test_case['passRate'] = 'NONE'
            
            # 填充API相关信息
            test_case['apiDefinitionName'] = api_info.get('name', '')
            test_case['method'] = api_info.get('method', '')
            test_case['path'] = api_info.get('path', '')
            
            # 确保request字段存在
            if 'request' not in test_case:
                test_case['request'] = {}
            
            # 验证断言配置（新增）
            self._validate_assertions(test_case)
            
            # 处理请求配置
            test_case['request'] = self._process_request_config(test_case['request'], api_info)
            
            return test_case
            
        except Exception as e:
            logger.error(f"后处理测试用例失败: {e}")
            return test_case
    
    def _process_request_config(self, request_template: Dict[str, Any], 
                               api_info: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求配置：根据API信息填充具体值"""
        try:
            api_request = api_info.get('request', {})
            
            # 复制API的请求配置
            request_template['path'] = api_info.get('path', '')
            request_template['method'] = api_info.get('method', '')
            request_template['headers'] = api_request.get('headers', [])
            request_template['query'] = api_request.get('query', [])
            request_template['body'] = api_request.get('body', {})
            
            # 确保必要的字段存在
            if 'polymorphicName' not in request_template:
                request_template['polymorphicName'] = 'MsHTTPElement'
            if 'enable' not in request_template:
                request_template['enable'] = True
            
            return request_template
            
        except Exception as e:
            logger.error(f"处理请求配置失败: {e}")
            return request_template
    
    # 兜底用例逻辑已移除：若模型失败/解析失败，直接返回 None 由上层忽略该用例

    def generate_test_cases_for_apis_batch(self, api_definitions: List[Dict], 
                                       selected_apis: List[str], count_per_api: int, 
                                       priority: str) -> Dict:
        """批量生成测试用例（多线程生成，主线程合并）"""
        try:
            # 建立 path -> api_def 的索引，便于快速定位
            path_to_api: Dict[str, Dict[str, Any]] = {}
            for api in api_definitions:
                api_path = api.get('path')
                if api_path:
                    path_to_api[api_path] = api

            # 过滤有效的选择（根据文件中实际存在的 path）
            valid_paths = [p for p in selected_apis if p in path_to_api]
            if not valid_paths:
                return {
                    'success': False,
                    'message': '未找到有效的接口路径',
                }

            logger.info(f"开始并发生成。选中接口数: {len(valid_paths)}，每个接口生成: {count_per_api} 条")

            # 子线程只负责生成，不改动 api_definitions
            results_by_path: Dict[str, List[Dict[str, Any]]] = {p: [] for p in valid_paths}

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_key = {}
                for api_path in valid_paths:
                    api_def = path_to_api[api_path]
                    for case_num in range(1, count_per_api + 1):
                        fut = executor.submit(self._generate_single_test_case, api_def, priority, case_num)
                        future_to_key[fut] = (api_path, case_num, api_def.get('name', ''))

                for fut in as_completed(future_to_key):
                    api_path, case_num, api_name = future_to_key[fut]
                    try:
                        test_case = fut.result()
                        if test_case:
                            results_by_path[api_path].append(test_case)
                            logger.info(f"生成完成: {api_name} - 用例{case_num}")
                        else:
                            logger.warning(f"生成失败: {api_name} - 用例{case_num}")
                    except Exception as e:
                        logger.error(f"生成异常: {api_name} - 用例{case_num}: {e}")

            # 主线程合并结果到 api_definitions
            total_cases = 0
            for api_path, cases in results_by_path.items():
                api_def = path_to_api[api_path]
                if 'apiTestCaseList' not in api_def or not isinstance(api_def['apiTestCaseList'], list):
                    api_def['apiTestCaseList'] = []
                api_def['apiTestCaseList'].extend(cases)
                total_cases += len(cases)

            return {
                'success': True,
                'message': f'成功为{len(valid_paths)}个接口新增生成了测试用例，共 {total_cases} 条',
                'generated_cases': total_cases,
                'selected_api_count': len(valid_paths)
            }

        except Exception as e:
            logger.error(f"批量生成测试用例失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _get_default_assertion(self):
        """获取默认断言"""
        return {
            "assertionType": "RESPONSE_CODE",
            "enable": True,
            "name": "默认状态码验证",
            "id": "default_status_code",
            "projectId": None,
            "condition": "EQUALS",
            "expectedValue": "200"
        }
    
    def _validate_assertions(self, test_case):
        """验证大模型生成的断言结构"""
        allowed_types = ['RESPONSE_CODE', 'RESPONSE_HEADER', 'RESPONSE_BODY', 'VARIABLE', 'SCRIPT']
        
        if 'request' in test_case and 'children' in test_case['request']:
            for child in test_case['request']['children']:
                if 'assertionConfig' in child and 'assertions' in child['assertionConfig']:
                    assertions = child['assertionConfig']['assertions']
                    valid_assertions = []
                    
                    for assertion in assertions:
                        assertion_type = assertion.get('assertionType')
                        if assertion_type not in allowed_types:
                            logger.warning(f"不支持的断言类型: {assertion_type}，将跳过此断言")
                            continue
                        
                        # 验证断言结构的完整性
                        if self._validate_assertion_structure(assertion, assertion_type):
                            valid_assertions.append(assertion)
                        else:
                            logger.warning(f"断言结构不完整: {assertion_type}")
                    
                    # 更新为验证后的断言
                    child['assertionConfig']['assertions'] = valid_assertions
                    
                    # 如果没有有效断言，添加默认断言
                    if not valid_assertions:
                        logger.info("未找到有效断言，添加默认状态码断言")
                        child['assertionConfig']['assertions'] = [self._get_default_assertion()]

    def _validate_assertion_structure(self, assertion, assertion_type):
        """验证特定类型断言的结构完整性"""
        if assertion_type == 'RESPONSE_CODE':
            required_fields = ['enable', 'name', 'condition', 'expectedValue']
        elif assertion_type == 'RESPONSE_HEADER':
            required_fields = ['enable', 'name', 'assertions']
        elif assertion_type == 'RESPONSE_BODY':
            required_fields = ['enable', 'name', 'assertionBodyType', 'jsonPathAssertion']
        elif assertion_type == 'VARIABLE':
            required_fields = ['enable', 'name', 'variableAssertionItems']
        elif assertion_type == 'SCRIPT':
            required_fields = ['enable', 'name', 'script', 'scriptLanguage']
        else:
            return False
        
        return all(field in assertion for field in required_fields)


def parse_api_definitions(file_path: str) -> List[Dict]:
    """解析API定义文件，提取接口列表"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        api_list = []
        for api in data.get('apiDefinitions', []):
            case_count = len(api.get('apiTestCaseList', []))
            api_list.append({
                'path': api.get('path', ''),
                'name': api.get('name', ''),
                'method': api.get('method', ''),
                'has_test_cases': case_count > 0,
                'test_case_count': case_count
            })
        
        return api_list
    except Exception as e:
        logger.error(f"解析API定义文件失败: {e}")
        return []


def generate_test_cases_for_apis(file_path: str, selected_apis: list, count_per_api: int, 
                                 priority: str, llm_provider: str) -> Dict:
    """为选中的API生成测试用例"""
    try:
        # 读取原文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 创建Agent
        agent = APITestCaseGeneratorAgent(llm_provider)
        
        # 批量生成测试用例
        result = agent.generate_test_cases_for_apis_batch(
            data['apiDefinitions'], selected_apis, count_per_api, priority
        )
        
        if result['success']:
            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return result
        
    except Exception as e:
        logger.error(f"生成测试用例失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    

