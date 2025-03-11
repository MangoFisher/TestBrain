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
        
    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相关知识"""
        # 获取查询的嵌入向量
        query_embedding = self.embedder.get_embeddings(query)[0]
        self.logger.info(f"查询文本: '{query}', 向量维度: {len(query_embedding)}, 前5个维度: {query_embedding[:5]}")

        
        # 在向量数据库中搜索
        results = self.vector_store.search(query_embedding, top_k=top_k)
        
        return results 

    def search_relevant_knowledge(self, query: str, top_k: int = 5) -> str:
        """
        搜索跟输入文本相关的测试用例
        
        Args:
            query: 查询文本
            
        Returns:
            str: 跟查询需求有关的测试用例内容，如果没有找到则返回空字符串
        """
        self.logger.info(f"搜索知识: {query}")
        try:
            # 复用已有的search_knowledge函数
            results = self.search_knowledge(query, top_k=top_k)
            # self.logger.info(f"知识库搜索结果: {results}")
            
            if not results:
                return ""
            
            # 过滤掉第一条（因为它是查询本身）并处理其余结果
            valid_results = [r for r in results[1:] if r['case_name'] and r['steps'] and r['expected']]
            
            # 拼接测试用例文本
            knowledge_texts = []
            for item in valid_results:
                case_text = (
                    f"测试用例描述: {item['case_name'].strip()}\n"
                    f"测试步骤:\n{item['steps'].strip()}\n"
                    f"预期结果:\n{item['expected'].strip()}"
                )
                knowledge_texts.append(case_text)
            
            return "\n\n".join(knowledge_texts)
            
        except Exception as e:
            self.logger.warning(f"获取知识上下文失败: {str(e)}")
            return ""