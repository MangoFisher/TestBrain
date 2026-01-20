"""
LLM 最小输出的解析器模块
提供从文本到 MinimalCase 列表的解析功能，替代裸 json.loads
"""
import json
from typing import List
from pydantic import ValidationError
from langchain_core.output_parsers import PydanticOutputParser
from .api_test_case_schema import MinimalCase

# 建立 Pydantic 解析器
api_test_case_parser = PydanticOutputParser(pydantic_object=MinimalCase)


def clean_json_fence(text: str) -> str:
    """清理 LLM 输出中的 ```json ... ``` 包裹"""
    s = text.strip()
    if s.startswith('```json'):
        s = s[7:]
    if s.endswith('```'):
        s = s[:-3]
    return s.strip()


def parse_minimal_cases_or_raise(response_text: str) -> List[MinimalCase]:
    """
    解析 LLM 响应为 MinimalCase 列表
    
    Args:
        response_text: LLM 的原始字符串输出
        
    Returns:
        List[MinimalCase]: 解析后的结构化对象列表
        
    Raises:
        ValidationError: 字段缺失或类型错误
        json.JSONDecodeError: JSON 格式错误
    """
    cleaned = clean_json_fence(response_text)
    parsed = json.loads(cleaned)  # 若 JSON 不合法，直接抛 JSONDecodeError

    # 统一转为列表处理（支持 LLM 返回单个对象或数组）
    items = parsed if isinstance(parsed, list) else [parsed]
    results: List[MinimalCase] = []
    
    for item in items:
        # 交给 parser 做字段/类型校验与转换（失败会抛 ValidationError）
        obj = api_test_case_parser.parse(json.dumps(item, ensure_ascii=False))
        results.append(obj)
    
    return results


def get_format_instructions() -> str:
    """
    获取格式说明文本，用于注入到 prompt 中强约束 LLM 输出结构
    
    Returns:
        str: 格式说明文本
    """
    return api_test_case_parser.get_format_instructions()
