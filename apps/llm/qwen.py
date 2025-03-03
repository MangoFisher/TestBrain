import requests
import os
import time
from typing import Dict, Any, List
from .base import BaseLLMService

class QwenLLMService(BaseLLMService):
    """阿里Qwen大模型服务实现"""
    
    def __init__(self, api_key: str = None, api_url: str = None, model: str = "qwen-max", **kwargs):
        super().__init__()  # 调用父类初始化方法，设置logger
        
        # 如果没有提供API密钥，尝试从环境变量获取
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        if not self.api_key:
            self.logger.error("Qwen API key未提供")
            raise ValueError("Qwen API key is required. Set it via QWEN_API_KEY environment variable or pass it directly.")
            
        self.api_url = api_url or os.getenv("QWEN_API_URL", "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation")
        self.model = model
        
        # 记录额外的参数
        for key, value in kwargs.items():
            self.logger.debug(f"忽略额外参数: {key}={value}")
        
        self.logger.info(f"初始化QwenLLMService: model={model}, api_url={self.api_url}")
        
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本响应"""
        self._log_request("generate", prompt, **kwargs)
        start_time = time.time()
        
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.generate_with_history(messages, **kwargs)
            elapsed_time = time.time() - start_time
            self._log_response("generate", response, elapsed_time)
            return response
        except Exception as e:
            elapsed_time = time.time() - start_time
            self._log_error("generate", e, elapsed_time)
            raise
    
    def generate_with_history(self, 
                             messages: List[Dict[str, str]], 
                             **kwargs) -> str:
        """基于对话历史生成响应"""
        self._log_request("generate_with_history", messages, **kwargs)
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "input": {
                    "messages": messages
                },
                **kwargs
            }
            
            self.logger.debug(f"发送请求到Qwen API: {self.api_url}")
            response = requests.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_msg = f"Qwen API返回错误: 状态码={response.status_code}, 响应={response.text}"
                self.logger.error(error_msg)
                response.raise_for_status()
            
            response_json = response.json()
            result = response_json["output"]["text"]
            
            elapsed_time = time.time() - start_time
            self._log_response("generate_with_history", result, elapsed_time)
            
            # 记录额外的响应信息
            if "usage" in response_json:
                usage = response_json["usage"]
                self.logger.info(f"Token使用情况: 输入={usage.get('input_tokens', 0)}, "
                                f"输出={usage.get('output_tokens', 0)}, "
                                f"总计={usage.get('total_tokens', 0)}")
            
            return result
        except Exception as e:
            elapsed_time = time.time() - start_time
            self._log_error("generate_with_history", e, elapsed_time)
            raise 