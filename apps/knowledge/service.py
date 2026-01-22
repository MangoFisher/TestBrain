from .vector_store import MilvusVectorStore
from .embedding import BGEM3Embedder
from ..core.models import KnowledgeBase
# from typing import List, Dict, Any
from apps.utils.logger_manager import get_logger

class KnowledgeService:
    """知识库服务，整合向量存储和嵌入模型"""
    
    def __init__(self, vector_store: MilvusVectorStore, embedder: BGEM3Embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.logger = get_logger(self.__class__.__name__)
        
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
        
    def search_relevant_knowledge(self, query: str, top_k: int = 5, min_score_threshold: float = 0.6) -> str:
        """搜索相关知识
        
        Args:
            query: 查询文本
            top_k: 返回的最大结果数量
            min_score_threshold: 最小相似度阈值，低于此值的结果将被过滤掉
        
        Returns:
            组合后的相关知识文本
        """
        # 获取查询的嵌入向量
        query_embedding = self.embedder.get_embeddings(query)[0]
        self.logger.info(
            f"知识库查询context: '{query}'\n"
            f"向量维度: {len(query_embedding)}\n"
        )
        
        # 在向量数据库中搜索，获取更多结果以便后续过滤
        search_k = top_k * 3  # 获取更多结果用于后续过滤
        results = self.vector_store.search(query_embedding, top_k=search_k)
        # self.logger.info(f"知识库搜索原始结果: {results}")
        
        # 1. 相似度阈值过滤：过滤掉相似度低于阈值的结果
        threshold_filtered = [item for item in results if item["score"] >= min_score_threshold]
        self.logger.info(f"知识库搜索相似度阈值过滤后结果: {threshold_filtered}")
        # 2. 按照score从大到小排序
        sorted_results = sorted(threshold_filtered, key=lambda x: x["score"], reverse=True)
        
        # 3. 关键词后处理过滤：检查结果是否包含查询词的任何部分
        # 将查询拆分为关键词
        keywords = [kw.strip() for kw in query.split() if len(kw.strip()) > 1]
        
        keyword_filtered = []
        for item in sorted_results:
            content = item.get("content", "")
            # 检查内容是否包含任何关键词
            if any(keyword in content for keyword in keywords):
                keyword_filtered.append(item)
            elif len(keyword_filtered) < 2:  # 保留少量高分但不包含关键词的结果
                keyword_filtered.append(item)
        self.logger.info(f"知识库搜索关键词过滤后结果: {keyword_filtered}")
        # 4. 取前top_k个结果
        top_results = keyword_filtered[:top_k]
        self.logger.info(f"知识库搜索前top_k个结果: {top_results}")
        
        # 5. 提取content字段并组装成字符串
        content_list = [item["content"] for item in top_results if "content" in item]
        
        # 如果没有结果，返回提示信息
        if not content_list:
            return ""
        
        # 组装成字符串
        combined_content = "\n\n".join(content_list)
        
        return combined_content

   