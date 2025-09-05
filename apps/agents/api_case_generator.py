import json
import time
import copy
import os
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompts import APITestCaseGeneratorPrompt
from ..llm.base import LLMServiceFactory
from .parsers.api_test_case_parser import parse_minimal_cases_or_raise
from .parsers.retry_utils import generate_with_retry

logger = logging.getLogger(__name__)

class APITestCaseGeneratorAgent:
    """API测试用例生成Agent"""
    
    def __init__(self, llm_provider: str = "deepseek"):
        self.llm_provider = llm_provider
        self.llm = LLMServiceFactory.create(llm_provider)
        self.prompt = APITestCaseGeneratorPrompt()
        self.test_case_full_template = self._load_test_case_full_template()
        self.max_workers = 5
    
    def _has_request_parameters(self, api_info: Dict[str, Any]) -> bool:
        """判断接口是否包含任何请求参数（query/rest/body(JSON)）。
        - query/rest: 非空列表视为有参数
        - body(JSON): jsonBody.jsonValue 可解析且含键，或 jsonSchema.properties 含键
        """
        request = api_info.get('request') or {}

        # query
        query_params = request.get('query')
        if isinstance(query_params, list) and len(query_params) > 0:
            return True

        # rest
        rest_params = request.get('rest')
        if isinstance(rest_params, list) and len(rest_params) > 0:
            return True

        # body (JSON)
        body = request.get('body')
        if isinstance(body, dict) and body.get('bodyType') == 'JSON':
            json_body = body.get('jsonBody', {}) or {}
            # 先看 jsonValue 是否有实际键值
            json_value_str = json_body.get('jsonValue')
            if isinstance(json_value_str, str) and json_value_str.strip():
                try:
                    parsed = json.loads(json_value_str)
                    if isinstance(parsed, dict) and len(parsed) > 0:
                        return True
                except Exception:
                    # 解析失败则继续看 schema
                    pass
            # 再看 schema properties
            props = (json_body.get('jsonSchema') or {}).get('properties') or {}
            if isinstance(props, dict) and len(props) > 0:
                return True

        return False

    def _load_test_case_full_template(self) -> Dict[str, Any]:
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
        """为某个api接口一次生成多条测试用例（单次LLM调用返回数组）
        使用最小输出协议，仅让LLM生成差异字段，然后在本地合并为完整模板。
        使用 Pydantic 解析和自动重试机制。
        """
        try:
            # 使用新的解析和重试机制
            minimal_cases = self._generate_with_retry(api_info, priority, count)
            if not minimal_cases:
                return None

            # 合并为完整用例
            processed: List[Dict[str, Any]] = []
            for mcase in minimal_cases:
                try:
                    # 将 Pydantic 对象转换为 dict
                    mcase_dict = mcase.dict() if hasattr(mcase, 'dict') else mcase
                    processed.append(self._merge_minimal_case_to_full_case(mcase_dict, api_info, priority))
                except Exception as e:
                    logger.error("合并最小用例失败: %s", e)
            return processed
        except Exception as e:
            logger.error("生成多条测试用例失败: %s", e)
            return None

    

    
    
    def _create_minimal_generation_template(self) -> Dict[str, Any]:
        return {
            "id": "TC-001",
            "name": "用例名称(接口名称_测试点描述, ≤40字)",
            "description": "用例描述(≤60字, 可选)",
            "request_body_json": { 
                "param_name": "要测试的参数名(如: isVirtually)",
                "param_value": "测试用的参数值(如: 1)"     
            },
            "request_query": [
                {
                    "param_name": "要测试的参数名(如: pageSize)",
                    "param_value": "测试用的参数值(如: 10)"
                }
            ],
            "request_rest": [
                {
                    "param_name": "要测试的参数名(如: userCode)",
                    "param_value": "测试用的参数值(如: oa1922897972947259394)"
                }
            ],
            "assertion_condition": "断言条件, 根据测试参数是否全部正确或不正确, 取值只能为EQUALS或NOT_EQUALS"
        }

    def _build_messages_minimal(self, api_info: Dict[str, Any], priority: str, count: int, 
                               include_format_instructions: bool = False) -> list:
        minimal_template = self._create_minimal_generation_template()
        return self.prompt.format_messages(
            api_info=api_info,
            priority=priority,
            case_count=count,
            api_test_case_min_template=json.dumps(minimal_template, ensure_ascii=False, indent=2),
            include_format_instructions=include_format_instructions
        )

    def _generate_with_retry(self, api_info: Dict[str, Any], priority: str, count: int) -> Optional[List]:
        """使用重试机制生成最小用例"""
        
        include_format_instructions = False  # 首次不带，重试时再带上

        # 定义一次 LLM 调用函数
        def call_llm_once():
            messages = self._build_messages_minimal(
                api_info, priority, count,
                include_format_instructions=include_format_instructions
            )
            
            # 打印完整提示词
            try:
                prompt_text = "\n\n".join([getattr(m, 'content', str(m)) for m in messages])
                logger.info("[LLM Prompt-MULTI] API=%s Count=%s\n%s", api_info.get('name', ''), count, prompt_text)
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
            
            logger.info("大模型多用例原始响应: %s", response)
            return response

        # 定义重试时的回调（增强提示词）
        def on_retry(attempt):
            logger.warning("解析失败，第 %d 次重试，增强格式约束", attempt + 1)
            # 重试时减少生成数量，提高成功率
            nonlocal count
            count = max(1, count // 2)
            # 从下一次开始追加严格的格式说明
            nonlocal include_format_instructions
            include_format_instructions = True

        # 执行重试生成
        try:
            return generate_with_retry(
                call_llm=call_llm_once,
                parse_cases=parse_minimal_cases_or_raise,
                on_retry=on_retry,
                max_retries=2
            )
        except Exception as e:
            logger.error("重试后仍失败: %s", e)
            return None

    def _merge_minimal_case_to_full_case(self, minimal_case: Dict[str, Any], api_info: Dict[str, Any], priority: str) -> Dict[str, Any]:
        '''使用模版文件中定义的测试用例模版结构, 并将大模型生成的参数、断言回填到模版中, 构成一个合法的测试用例'''
        full_case = copy.deepcopy(self.test_case_full_template)
        # 1.直接复用接口定义中的request结构, 参数和断言部分由大模型生成后回填
        full_case['request'] = copy.deepcopy(api_info.get('request')) 

        req = full_case.get('request')
        child0 = req['children'][0]

        # 2.填充用户设置的用例优先级和代码中设置的用例标签
        full_case['priority'] = priority
        full_case['tags'] = ['TestBrain']

        # 3.填充用例名称
        name = minimal_case.get('name') or 'TestBrain生成的用例'
        full_case['name'] = name
        full_case['request']['name'] = name

        # 4.将需要大模型生成的参数回填到full_case中的request字段
        self._apply_minimal_request_overrides(full_case, minimal_case, api_info)

        # 5. 后端固定生成断言，只使用 LLM 的 condition
        assertion_condition = minimal_case.get('assertion_condition', 'EQUALS')
        fixed_assertion = self._generate_fixed_assertion(assertion_condition)
        
        child0['assertionConfig']['assertions'] = [fixed_assertion]

        return full_case


    def _apply_minimal_request_overrides(self, full_case: Dict[str, Any], minimal_case: Dict[str, Any], api_info: Dict[str, Any]) -> None:
        """将 LLM 生成的差异值应用到 request（body/query/rest），同时同步API定义中的类型信息"""
        req = full_case.get('request', {})
        
        if 'request_body_json' in minimal_case:
            # 严格校验 body 必备结构，缺失即报错，避免静默兜底掩盖问题
            body = req.get('body')
            if not isinstance(body, dict):
                raise ValueError("非法request：缺少 body 或类型错误")
            json_body = body.get('jsonBody')
            if not isinstance(json_body, dict):
                raise ValueError("非法request：缺少 body.jsonBody 或类型错误")
            data_by_type = body.get('bodyDataByType')
            if not isinstance(data_by_type, dict):
                raise ValueError("非法request：缺少 body.bodyDataByType 或类型错误")

            json_value_str = json.dumps(minimal_case['request_body_json'], ensure_ascii=False, indent=2)
            json_body['jsonValue'] = json_value_str
            data_by_type['jsonValue'] = json_value_str
        
        if 'request_query' in minimal_case:
            llm_query = minimal_case['request_query'] or []
            full_case_query = req.get('query', [])

            # 创建API定义中query参数的映射表
            full_case_query_map: Dict[str, Any] = {}
            for param in full_case_query:
                param_key = param.get('key') or param.get('name')
                if param_key:
                    full_case_query_map[param_key] = param

            # 合并：复制API参数结构，仅覆盖value
            merged_query: List[Dict[str, Any]] = []
            for llm_param in llm_query:
                q_name = llm_param.get('param_name') or llm_param.get('key') or llm_param.get('name')
                q_value = llm_param.get('param_value') or llm_param.get('value')
                if q_name in full_case_query_map:
                    api_param = full_case_query_map[q_name]
                    merged_param = api_param.copy()
                    merged_param['value'] = q_value
                    merged_query.append(merged_param)
                else:
                    logger.warning(f"API定义中未找到query参数: {q_name}")

            req['query'] = merged_query
        
        if 'request_rest' in minimal_case:
            llm_rest = minimal_case['request_rest'] or []
            full_case_rest = req.get('rest', [])
            
            # 创建API定义中rest参数的映射表
            full_case_rest_map = {}
            for param in full_case_rest:
                param_key = param.get('key') or param.get('name')
                if param_key:
                    full_case_rest_map[param_key] = param
            
            # 合并LLM生成的值，同时同步API定义中的类型信息
            merged_rest = []
            for llm_param in llm_rest:
                # LLM生成的是简化的参数信息
                param_name = llm_param.get('param_name') or llm_param.get('key')
                param_value = llm_param.get('param_value') or llm_param.get('value')
                
                if param_name in full_case_rest_map:
                    # 如果API定义中有这个参数，使用完整的API定义结构
                    api_param = full_case_rest_map[param_name]
                    merged_param = api_param.copy()  # 复制完整的API定义结构
                    merged_param['value'] = param_value  # 只更新value字段
                    merged_rest.append(merged_param)
                else:
                    # 如果API定义中没有，记录警告并跳过
                    logger.warning(f"API定义中未找到参数: {param_name}")
            
            req['rest'] = merged_rest
        
        full_case['request'] = req
    
    
    
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

            logger.info(f"合并完成，共为 {len(results_by_path)} 个接口合并了 {total_cases} 条测试用例")
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
        api_name = api_def.get('name', '')
        try:
            # 保护性判断：无参数则不调用模型
            if not self._has_request_parameters(api_def):
                logger.info("接口 query、rest、body 均无请求参数，跳过 LLM 生成用例：%s", api_name)
                return []
            cases = self._generate_multiple_test_cases(api_def, priority, count_per_api) or []
            logger.info("接口生成完成: %s - 新增用例 %d 条", api_name, len(cases))
            return cases
        except Exception as e:
            logger.error("接口多用例生成异常: %s: %s", api_name, e)
            return []

    def _generate_fixed_assertion(self, condition: str) -> Dict[str, Any]:
        """后端固定生成断言结构，只让 LLM 决定 condition"""
        ts = int(time.time() * 1000)
        return {
            "assertionType": "RESPONSE_BODY",
            "enable": True,
            "name": "响应体",
            "id": f"{ts}",
            "projectId": None,
            "assertionBodyType": "JSON_PATH",
            "jsonPathAssertion": {
                "assertions": [{
                    "enable": True,
                    "expression": "code",
                    "condition": condition,
                    "expectedValue": "10000",
                    "valid": True
                }]
            },
            "xpathAssertion": {"responseFormat": "XML", "assertions": []},
            "documentAssertion": None,
            "regexAssertion": {"assertions": []},
            "bodyAssertionClassByType": "io.metersphere.project.api.assertion.body.MsJSONPathAssertion",
            "bodyAssertionDataByType": {
                "assertions": [{
                    "enable": True,
                    "expression": "code",
                    "condition": condition,
                    "expectedValue": "10000",
                    "valid": True
                }]
            }
        }

    


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
    

