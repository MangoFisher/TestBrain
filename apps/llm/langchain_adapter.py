#TODO:确定没有使用后需要删除
# from typing import Any, List, Optional
# from langchain_core.messages import BaseMessage
# from langchain_core.callbacks.manager import CallbackManagerForLLMRun
# from .base import BaseLLMService

# class LangChainAdapter(BaseLLMService):
#     """LangChain适配器"""
    
#     def __init__(self, model):
#         """初始化
#         Args:
#             model: LangChain模型实例
#         """
#         self.model = model
#         super().__init__()

#     def _generate(
#         self,
#         messages: List[BaseMessage],
#         stop: Optional[List[str]] = None,
#         run_manager: Optional[CallbackManagerForLLMRun] = None,
#         **kwargs: Any,
#     ) -> str:
#         """调用模型生成响应"""
#         response = self.model.invoke(messages)
#         return response
    
#     @property
#     def _llm_type(self) -> str:
#         return "langchain_adapter"