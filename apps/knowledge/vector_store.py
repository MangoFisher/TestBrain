#TODO: 检索优化
'''
开发者可根据具体需求组合使用，例如在 RAG 系统中：
用稀疏检索召回包含关键词的文档（如 “合同”“解除”）。
用稠密检索对结果按语义相关性排序（如 “合同解除条款” 优先于 “合同签订流程”）。
用多向量检索对前 50 篇文档的具体段落进行细粒度匹配（如 “单方面解除条件”）
'''

from pymilvus import connections, Collection, utility, DataType
from pymilvus import CollectionSchema, FieldSchema
import numpy as np
from typing import List, Dict, Any, Optional
import os
from django.conf import settings
from utils.logger_manager import get_logger

logger = get_logger(__name__)

class MilvusVectorStore:
    """Milvus向量数据库服务"""
    
    def __init__(self, 
                host: str = "localhost", 
                port: str = "19530",
                collection_name: str = "vv_knowledge_collection"):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        # 原来的逻辑
        self._connect()
        self._ensure_collection()

        # 从Django配置文件中读取ENABLE_MILVUS设置
        # if getattr(settings, 'ENABLE_MILVUS', False):
        #     self._connect()
        #     self._ensure_collection()
        # else:
        #     print("Milvus connection disabled in settings")
        
    def _connect(self):
        """连接到Milvus服务器"""
        connections.connect(
            alias="default", 
            host=self.host,
            port=self.port
        )
        
    def _ensure_collection(self):
        """确保集合存在，如不存在则创建"""
        logger.info("进入到_ensure_collection方法")
        if not utility.has_collection(self.collection_name):
            logger.info(f"集合 {self.collection_name} 不存在，开始创建...")
            # 定义集合模式
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.INT64,
                    is_primary=True,
                    auto_id=True
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=1024  
                ),
                FieldSchema(
                    name="content",    # 存储文档片段的实际内容
                    dtype=DataType.VARCHAR,
                    max_length=4096
                ),
                FieldSchema(
                    name="metadata",   # 存储文档的元数据（JSON格式字符串）
                    dtype=DataType.VARCHAR,
                    max_length=1024
                ),
                FieldSchema(
                    name="source",     # 原始文档的来源信息（文件路径或URL）
                    dtype=DataType.VARCHAR,
                    max_length=512
                ),
                FieldSchema(
                    name="doc_type",   # 文档类型（pdf/doc/excel等）
                    dtype=DataType.VARCHAR,
                    max_length=32
                ),
                FieldSchema(
                    name="chunk_id",   # 分片ID，用于追踪文档的不同部分
                    dtype=DataType.VARCHAR,
                    max_length=128
                ),
                FieldSchema(
                    name="upload_time",
                    dtype=DataType.VARCHAR,
                    max_length=50
                )  # 添加存储时间的字段
            ]
            schema = CollectionSchema(fields=fields, description="vv知识库")
            collection = Collection(name=self.collection_name, schema=schema)
            logger.info("集合创建成功")
            
            # 创建索引
            logger.info("开始创建索引...")
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64}
            }
            collection.create_index(
                field_name="embedding", 
                index_params=index_params
            )
            logger.info("索引创建成功")
            collection.load()
            return collection
        else:
            logger.info(f"集合 {self.collection_name} 已存在，直接返回")
            collection = Collection(self.collection_name)
            collection.load()
            return collection
        
    def add_data(self, data: List[Dict[str, Any]]):
        """添加文档到向量数据库"""
        logger.info("进入到add_data方法")
        collection = Collection(self.collection_name)

        try:
            collection.insert(data)
        except Exception as e:
            raise
                
        collection.flush()
        
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索最相似的文档"""
        collection = Collection(self.collection_name)
        collection.load()
        
        search_params = {"metric_type": "COSINE", "params": {"ef": 32}}
        results = collection.search(
            data=[query_vector], 
            anns_field="embedding", 
            param=search_params,
            limit=top_k,
            output_fields=[
                "content", "metadata", "source", 
                "doc_type", "chunk_id", "upload_time"
            ]
        )
        
        ret = []
        for hits in results:
            for hit in hits:
                ret.append({
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.entity.get("content"),
                    "metadata": hit.entity.get("metadata"),
                    "source": hit.entity.get("source"),
                    "doc_type": hit.entity.get("doc_type"),
                    "chunk_id": hit.entity.get("chunk_id"),
                    "upload_time": hit.entity.get("upload_time")
                })
        
        collection.release()
        return ret 