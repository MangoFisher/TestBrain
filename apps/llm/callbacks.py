from langchain.callbacks.base import BaseCallbackHandler
from apps.utils.logger_manager import get_logger

class LoggingCallbackHandler(BaseCallbackHandler):
    """日志记录回调处理器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """LLM开始生成时的回调"""
        # prompt_preview = prompts[0][:100] + "..." if len(prompts[0]) > 100 else prompts[0]
        self.logger.info(f"开始LLM调用...")
    
    def on_llm_end(self, response, **kwargs):
        """LLM生成完成时的回调"""
        self.logger.info("LLM调用完成")
        self.logger.debug(f"LLM响应: {response}")
    
    def on_llm_error(self, error, **kwargs):
        """LLM生成出错时的回调"""
        self.logger.error(f"LLM调用出错: {str(error)}") 