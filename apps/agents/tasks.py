from celery import shared_task
from celery.utils.log import get_task_logger
from typing import Any, List, Dict
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from ..llm.base import BaseLLMService

logger = get_task_logger(__name__)

@shared_task(
    name="agents.llm_invoke",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True
)
def llm_invoke(llm_service_dict: Dict[str, Any], messages: List[Dict[str, Any]]) -> Any:
    """
    异步执行LLM调用
    
    Args:
        llm_service_dict: LLM服务实例的序列化字典
        messages: 消息列表的序列化形式
    
    Returns:
        Any: LLM响应结果
    """
    try:
        logger.info("开始重建LLM服务实例")
        
        # 从字典重建LLM服务实例
        llm_service = BaseLLMService.from_dict(llm_service_dict)
        logger.info("LLM服务实例重建成功")
        
        # 将序列化的消息转换回LangChain消息对象
        message_objects = []
        for msg_dict in messages:
            # 根据消息类型创建对应的消息对象
            msg_type = msg_dict.get('type')
            if msg_type == 'system':
                message_objects.append(SystemMessage(**msg_dict))
            elif msg_type == 'human':
                message_objects.append(HumanMessage(**msg_dict))
            elif msg_type == 'ai':
                message_objects.append(AIMessage(**msg_dict))
            else:
                message_objects.append(BaseMessage(**msg_dict))
        
        logger.info("开始调用LLM服务")
        # 调用LLM服务
        response = llm_service.invoke(message_objects)
        logger.info("LLM服务调用完成")
        return response.content
        
    except Exception as e:
        logger.error(f"LLM调用失败: {str(e)}")
        raise 