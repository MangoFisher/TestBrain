from .vector_store import MilvusVectorStore
from .embedding import BGEM3Embedder
from ..core.models import KnowledgeBase
from typing import List, Dict, Any
from utils.logger_manager import get_logger

class KnowledgeService:
    """知识库服务，整合向量存储和嵌入模型"""
    
    def __init__(self, vector_store: MilvusVectorStore, embedder: BGEM3Embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.logger = get_logger('knowledge')
        
    def add_knowledge(self, title: str, content: str) -> int:
        """添加知识到知识库"""
        # 获取嵌入向量
        embedding = self.embedder.get_embeddings(content)[0]
        
        # 添加到向量数据库
        self.vector_store.add_documents([{
            "title": title,
            "content": content,
            "embedding": embedding
        }])
        
        # 保存到MySQL
        knowledge = KnowledgeBase(
            title=title,
            content=content
        )
        knowledge.save()
        
        return knowledge.id
        
    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相关知识"""
        # 获取查询的嵌入向量
        query_embedding = self.embedder.get_embeddings(query)[0]
        
        # 在向量数据库中搜索
        results = self.vector_store.search(query_embedding, top_k=top_k)
        
        return results 

    def search_relevant_knowledge(self, query: str) -> str:
        """
        搜索相关知识
        
        Args:
            query: 查询文本
            
        Returns:
            str: 相关知识文本，如果没有找到则返回空字符串
        """
        # TODO: 实现知识搜索逻辑
        self.logger.info(f"搜索知识: {query}")
        return ""  # 暂时返回空字符串，后续实现具体搜索逻辑 