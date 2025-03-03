from pymilvus import connections, Collection, utility
from pymilvus import CollectionSchema, FieldSchema, DataType
import numpy as np
from typing import List, Dict, Any, Optional
import os
from django.conf import settings

class MilvusVectorStore:
    """Milvus向量数据库服务"""
    
    def __init__(self, 
                host: str = "localhost", 
                port: str = "19530",
                collection_name: str = "test_brain_knowledge"):
        self.host = host
        self.port = port
        self.collection_name = collection_name
        # 原来的逻辑
        # self._connect()

        # 从Django配置文件中读取ENABLE_MILVUS设置
        if getattr(settings, 'ENABLE_MILVUS', False):
            self._connect()
            self._ensure_collection()
        else:
            print("Milvus connection disabled in settings")
        
    def _connect(self):
        """连接到Milvus服务器"""
        connections.connect(
            alias="default", 
            host=self.host,
            port=self.port
        )
        
    def _ensure_collection(self):
        """确保集合存在，如不存在则创建"""
        if not utility.has_collection(self.collection_name):
            # 定义字段
            id_field = FieldSchema(
                name="id", 
                dtype=DataType.INT64, 
                is_primary=True, 
                auto_id=True
            )
            vector_field = FieldSchema(
                name="embedding", 
                dtype=DataType.FLOAT_VECTOR, 
                dim=1024  # BGE-M3的维度
            )
            content_field = FieldSchema(
                name="content", 
                dtype=DataType.VARCHAR, 
                max_length=65535
            )
            title_field = FieldSchema(
                name="title", 
                dtype=DataType.VARCHAR, 
                max_length=256
            )
            
            # 创建集合
            schema = CollectionSchema(
                fields=[id_field, vector_field, content_field, title_field],
                description="Test Brain Knowledge Base"
            )
            collection = Collection(
                name=self.collection_name, 
                schema=schema
            )
            
            # 创建索引
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64}
            }
            collection.create_index(
                field_name="embedding", 
                index_params=index_params
            )
            
    def add_documents(self, documents: List[Dict[str, Any]]):
        """添加文档到向量数据库"""
        collection = Collection(self.collection_name)
        
        # 准备数据
        vectors = [doc["embedding"] for doc in documents]
        contents = [doc["content"] for doc in documents]
        titles = [doc["title"] for doc in documents]
        
        # 插入数据
        collection.insert([
            vectors,
            contents,
            titles
        ])
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
            output_fields=["content", "title"]
        )
        
        ret = []
        for hits in results:
            for hit in hits:
                ret.append({
                    "id": hit.id,
                    "score": hit.score,
                    "content": hit.entity.get("content"),
                    "title": hit.entity.get("title")
                })
                
        collection.release()
        return ret 