from langchain_openai import ChatOpenAI
import os


class DeepSeekChatModel(ChatOpenAI):
    """DeepSeek聊天模型"""
    
    def __init__(
        self,
        api_key: str = None,
        api_base: str = None,
        model: str = "deepseek-chat",
        **kwargs
    ):
        # 设置默认的API基础URL
        api_base = api_base or "https://api.deepseek.com/v1"
        
        # 获取API密钥
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "DeepSeek API key is required. Set it via DEEPSEEK_API_KEY environment variable "
                "or pass it directly."
            )
        
        # 设置为OpenAI格式的API密钥
        os.environ["OPENAI_API_KEY"] = api_key
        
        super().__init__(
            model_name=model,
            openai_api_base=api_base,
            **kwargs
        )