from langchain_community.chat_models import ChatOpenAI
import os

class QwenChatModel(ChatOpenAI):
    """通义千问聊天模型"""
    
    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = "qwen-max",
        **kwargs
    ):
        # 设置默认的API基础URL
        api_base = api_base or "https://dashscope.aliyuncs.com/api/v1"
        
        # 获取API密钥
        api_key = api_key or os.getenv("QWEN_API_KEY")
        if not api_key:
            raise ValueError(
                "Qwen API key is required. Set it via QWEN_API_KEY environment variable "
                "or pass it directly."
            )
        
        # 设置为OpenAI格式的API密钥
        os.environ["OPENAI_API_KEY"] = api_key
        
        super().__init__(
            model_name=model,
            openai_api_base=api_base,
            **kwargs
        )