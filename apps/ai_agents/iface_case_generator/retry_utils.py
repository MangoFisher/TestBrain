"""
重试工具模块
提供解析失败时的自动重试机制
"""
from typing import List, Callable
from pydantic import ValidationError
import json


def generate_with_retry(
    call_llm: Callable[[], str],               # 执行一次 LLM 请求，返回字符串
    parse_cases: Callable[[str], List],        # 解析函数
    on_retry: Callable[[int], None],           # 每次失败时如何修改提示词
    max_retries: int = 2
) -> List:
    """
    带重试的生成和解析流程
    
    Args:
        call_llm: 执行一次 LLM 请求的函数
        parse_cases: 解析函数
        on_retry: 失败时的回调函数，用于修改提示词
        max_retries: 最大重试次数
        
    Returns:
        List: 解析后的结构化对象列表
        
    Raises:
        ValidationError: 解析失败
        json.JSONDecodeError: JSON 格式错误
    """
    last_err = None
    
    for attempt in range(max_retries + 1):
        try:
            raw = call_llm()
            return parse_cases(raw)
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            last_err = e
            if attempt == max_retries:
                raise e
            # 通知外部"下次要加强提示"或"减少生成条数"等
            on_retry(attempt)
    
    raise last_err
