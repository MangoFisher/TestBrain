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
                collection_name: str = "test_cases"):
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
                # 测试用例基本信息
                FieldSchema(
                    name="case_name",  # 用例名称
                    dtype=DataType.VARCHAR,
                    max_length=256
                ),
                FieldSchema(
                    name="case_id",    # 用例ID
                    dtype=DataType.VARCHAR,
                    max_length=64
                ),
                FieldSchema(
                    name="module",     # 所属模块
                    dtype=DataType.VARCHAR,
                    max_length=512
                ),
                # 测试用例详细内容
                FieldSchema(
                    name="precondition",  # 前置条件
                    dtype=DataType.VARCHAR,
                    max_length=1024
                ),
                FieldSchema(
                    name="steps",         # 步骤描述
                    dtype=DataType.VARCHAR,
                    max_length=4096
                ),
                FieldSchema(
                    name="expected",      # 预期结果
                    dtype=DataType.VARCHAR,
                    max_length=2048
                ),
                # 其他元数据
                FieldSchema(
                    name="tags",          # 标签
                    dtype=DataType.VARCHAR,
                    max_length=256
                ),
                FieldSchema(
                    name="priority",      # 用例等级
                    dtype=DataType.VARCHAR,
                    max_length=32
                ),
                FieldSchema(
                    name="creator",       # 创建人
                    dtype=DataType.VARCHAR,
                    max_length=64
                ),
                FieldSchema(
                    name="create_time",   # 创建时间
                    dtype=DataType.VARCHAR,
                    max_length=64
                )
            ]
            
            schema = CollectionSchema(fields=fields, description="测试用例知识库")
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
        
    def add_documents(self, documents: List[Dict[str, Any]]):
        """添加文档到向量数据库"""
        logger.info("进入到add_documents方法")
        collection = Collection(self.collection_name)
        
        # 打印第一条文档的内容，用于调试
        if documents:
            logger.info(f"First document content: {documents[0]}")
        
        # 准备数据
        embeddings = [doc["embedding"] for doc in documents]
        
        # 如果是 numpy array，先转换为列表
        if isinstance(embeddings[0], np.ndarray):
            embeddings = [emb.astype(np.float32) for emb in embeddings]
            
        # 一次插入一条记录
        for i, embedding in enumerate(embeddings):
            # 打印当前文档的所有字段，用于调试
            logger.info(f"Document {i} fields:")
            for key, value in documents[i].items():
                if key != "embedding":
                    logger.info("*"*100)
                    logger.info(f"{key}: {value}")
                    logger.info("*"*100)
                
            data = {
                "embedding": embedding,
                "case_name": str(documents[i].get("case_name", "")),  # 确保转换为字符串
                "case_id": str(documents[i].get("case_id", "")),
                "module": str(documents[i].get("module", "")),
                "precondition": str(documents[i].get("precondition", "")),
                "steps": str(documents[i].get("steps", "")),
                "expected": str(documents[i].get("expected", "")),
                "tags": str(documents[i].get("tags", "")),
                "priority": str(documents[i].get("priority", "")),
                "creator": str(documents[i].get("creator", "")),
                "create_time": str(documents[i].get("create_time", ""))
            }
            
            # 打印准备插入的数据，用于调试
            logger.info(f"Inserting data for document {i}:")
            for key, value in data.items():
                if key != "embedding":  # 不打印embedding，太长了
                    logger.info("$"*100)
                    logger.info(f"{key}: {value}")
                    logger.info("$"*100)
            try:
                collection.insert(data)
            except Exception as e:
                logger.error(f"Insert error at index {i}: {str(e)}")
                logger.error(f"Data keys: {data.keys()}")
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
                "case_name", "case_id", "module", 
                "precondition", "steps", "expected",
                "tags", "priority", "creator", "create_time"
            ]
        )
        
        ret = []
        for hits in results:
            for hit in hits:
                ret.append({
                    "id": hit.id,
                    "score": hit.score,
                    "case_name": hit.entity.get("case_name"),
                    "case_id": hit.entity.get("case_id"),
                    "module": hit.entity.get("module"),
                    "precondition": hit.entity.get("precondition"),
                    "steps": hit.entity.get("steps"),
                    "expected": hit.entity.get("expected"),
                    "tags": hit.entity.get("tags"),
                    "priority": hit.entity.get("priority"),
                    "creator": hit.entity.get("creator"),
                    "create_time": hit.entity.get("create_time")
                })
        
        collection.release()
        return ret 