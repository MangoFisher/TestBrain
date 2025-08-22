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
    
    
    
    def _generate_multiple_test_cases(self, api_info: Dict[str, Any], 
                                      priority: str, count: int) -> Optional[List[Dict[str, Any]]]:
        """一次生成多条测试用例（单次LLM调用返回数组）"""
        import threading
        thread_id = threading.current_thread().ident
        try:
            # 基于现有提示词，追加一次性生成多条的说明
            messages = self.prompt.format_messages(
                api_info=api_info,
                priority=priority,
                case_count=count,
                test_case_template=json.dumps(self.template, ensure_ascii=False, indent=2)
            )

            # 打印完整提示词
            try:
                prompt_text = "\n\n".join([getattr(m, 'content', str(m)) for m in messages])
                logger.info(f"[Thread-{thread_id}] [LLM Prompt-MULTI] API={api_info.get('name', '')} Count={count}\n{prompt_text}")
            except Exception:
                pass

            # 单次调用生成多条
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

            cases = self._parse_response_to_test_cases(response)
            if cases is None:
                return None

            # 后处理
            processed: List[Dict[str, Any]] = []
            for case in cases:
                try:
                    processed.append(self._post_process_test_case(case, api_info, priority))
                except Exception as e:
                    logger.error(f"[Thread-{thread_id}] 多用例后处理失败: {e}")
            return processed
        except Exception as e:
            logger.error(f"[Thread-{thread_id}] 生成多条测试用例失败: {e}")
            return None

    

    def _parse_response_to_test_cases(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        """解析大模型响应为测试用例列表（支持数组或单对象容错）"""
        try:
            if not isinstance(response, str):
                response = getattr(response, 'content', str(response))
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            parsed = json.loads(clean_response)
            if isinstance(parsed, list):
                return [p for p in parsed if isinstance(p, dict)]
            if isinstance(parsed, dict):
                return [parsed]
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解析多用例响应失败: {e}")
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
                future_to_path = {}
                for api_path in valid_paths:
                    api_def = path_to_api[api_path]
                    fut = executor.submit(self._generate_cases_for_single_api, api_def, priority, count_per_api)
                    future_to_path[fut] = (api_path, api_def.get('name', ''))

                for fut in as_completed(future_to_path):
                    api_path, api_name = future_to_path[fut]
                    try:
                        cases = fut.result() or []
                        results_by_path[api_path].extend(cases)
                        logger.info(f"接口生成完成: {api_name} - 新增用例 {len(cases)} 条")
                    except Exception as e:
                        logger.error(f"接口生成异常: {api_name}: {e}")

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

    def _generate_cases_for_single_api(self, api_def: Dict[str, Any], priority: str, count_per_api: int) -> List[Dict[str, Any]]:
        """为单个接口一次性生成多条测试用例（按接口并发，单次LLM调用）"""
        import threading
        thread_id = threading.current_thread().ident
        api_name = api_def.get('name', '')
        try:
            cases = self._generate_multiple_test_cases(api_def, priority, count_per_api) or []
            logger.info(f"[Thread-{thread_id}] 接口生成完成: {api_name} - 新增用例 {len(cases)} 条")
            return cases
        except Exception as e:
            logger.error(f"[Thread-{thread_id}] 接口多用例生成异常: {api_name}: {e}")
            return []

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
    

