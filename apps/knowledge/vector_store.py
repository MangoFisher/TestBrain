from pymilvus import connections, Collection, utility, DataType
from pymilvus import CollectionSchema, FieldSchema
# import numpy as np
from typing import List, Dict, Any, Optional
from django.conf import settings
from apps.utils.logger_manager import get_logger

logger = get_logger(__name__)

class MilvusVectorStore:
    """Milvus向量数据库服务"""
    
    def __init__(self, 
                host: Optional[str] = None, 
                port: Optional[str] = None,
                db_name: Optional[str] = None,
                collection_name: Optional[str] = None):
        config = getattr(settings, "VECTOR_DB_CONFIG", {}) or {}
        self.host = host or config.get("host", "localhost")
        self.port = port or config.get("port", "19530")
        self.db_name = db_name or config.get("db_name", "default")
        self.collection_name = collection_name or config.get("collection_name", "vv_knowledge_collection")
        # 仅在开启 Milvus 时建立连接；关闭时仍可构造对象，
        # 以免在未部署 Milvus 的环境中启动即失败。
        if getattr(settings, "ENABLE_MILVUS", False):
            self._connect()
            self._ensure_collection()
        else:
            logger.info("ENABLE_MILVUS 未开启，跳过 Milvus 连接与集合检查")
        
    def _connect(self):
        """连接到Milvus服务器"""
        connections.connect(
            alias="default", 
            host=self.host,
            port=self.port,
            db_name=self.db_name
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

        # 增加截断逻辑：遍历数据，确保 content 不超过 4096
        safe_data = []
        for item in data:
            content = item.get("content", "")
            if len(content) > 4096:
                logger.warning(f"检测到内容长度 {len(content)} 超过 4096，已执行强制截断。")
                item["content"] = content[:4092] + "..."
            safe_data.append(item)
        
        # 插入处理后的 safe_data
        collection.insert(safe_data)
        collection.flush()
    
    def delete_by_source(self, source_path: str):
        """根据文件路径删除文档的所有记录"""
        logger.info(f"开始删除文件 {source_path} 的向量记录")
        collection = Collection(self.collection_name)
        
        try:
            # 构建删除表达式：根据source字段删除
            expr = f'source == "{source_path}"'
            collection.delete(expr)
            collection.flush()
            logger.info(f"成功删除文件 {source_path} 的向量记录")
        except Exception as e:
            logger.error(f"删除文件 {source_path} 的向量记录失败: {str(e)}")
            raise
        
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