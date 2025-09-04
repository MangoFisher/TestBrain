"""
LLM 最小输出的 Pydantic 模型定义
用于约束和校验 LLM 生成的测试用例差异字段
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class JsonPathAssertionItem(BaseModel):
    """JSONPath 断言的一条明细规则，如 "code == 10000" """
    enable: bool = True
    expression: Literal['code'] = 'code'  # 断言表达式暂时只允许 "code"
    condition: Literal['EQUALS', 'NOT_EQUALS']  # 比较条件，只允许这两种
    expectedValue: str = Literal['10000']  # 期望值，按照模板保持字符串


class JsonPathAssertion(BaseModel):
    """jsonPathAssertion 结构体，固定包含 assertions 数组"""
    assertions: List[JsonPathAssertionItem] = Field(..., min_items=1)  # 至少包含一条断言


class ResponseBodyAssertion(BaseModel):
    """仅允许 RESPONSE_BODY + JSON_PATH 的完整断言对象"""
    assertionType: Literal['RESPONSE_BODY'] = 'RESPONSE_BODY'
    enable: bool = True
    name: Literal['响应体'] = '响应体'
    id: Optional[str] = None  # 后续会用时间戳覆盖
    projectId: Optional[str] = None
    assertionBodyType: Literal['JSON_PATH'] = 'JSON_PATH'
    # 使用具体的结构体而不是通用 Dict
    jsonPathAssertion: JsonPathAssertion
    xpathAssertion: Dict[str, Any] = {"responseFormat": "XML", "assertions": []}
    documentAssertion: Optional[Any] = None
    regexAssertion: Dict[str, List[Any]] = {"assertions": []}
    bodyAssertionClassByType: Literal['io.metersphere.project.api.assertion.body.MsJSONPathAssertion'] \
        = 'io.metersphere.project.api.assertion.body.MsJSONPathAssertion'
    bodyAssertionDataByType: JsonPathAssertion  # 与 jsonPathAssertion 结构相同


class MinimalRequestQueryParam(BaseModel):
    """LLM 最小输出的 query 参数差异"""
    param_name: str
    param_value: Optional[str] = None


class MinimalRequestRestParam(BaseModel):
    """LLM 最小输出的 rest 参数差异"""
    param_name: str
    param_value: Optional[str] = None


class MinimalCase(BaseModel):
    """单条最小用例（LLM 输出的一个对象）"""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=80)  # 用例名称（必填，最多80字符）
    description: Optional[str] = Field(None, max_length=200)  # 用例描述（可选）
    # 请求体的 JSON 差异（字典），后续会在合并时统一 json.dumps 成字符串写入 jsonValue
    request_body_json: Dict[str, Any] = Field(default_factory=dict)
    # query / rest 差异（只包含 param_name / param_value）
    request_query: List[MinimalRequestQueryParam] = Field(default_factory=list)
    request_rest: List[MinimalRequestRestParam] = Field(default_factory=list)
    # 断言列表（只允许 RESPONSE_BODY）
    assertions: List[ResponseBodyAssertion] = Field(default_factory=list)

    # 说明：此前使用的 @validator 被移除。该校验点在模型中通过更严格的类型定义
    # 已自然保证（断言类型只建模为 ResponseBodyAssertion）。
