"""
Milvus 向量数据库操作助手
"""

import pandas as pd
from pymilvus import connections, Collection, DataType, utility, FieldSchema, CollectionSchema
from sentence_transformers import SentenceTransformer
from apps.knowledge.vector_store import MilvusVectorStore
from utils.logger_manager import get_logger

logger = get_logger('milvus_helper')    

# 初始化嵌入模型（单例模式）
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True)
    return _embedding_model

# 初始化Milvus集合
def init_milvus_collection(collection_name="test_cases"):
    """初始化Milvus集合"""
    logger.info("进入到init_milvus_collection方法")
    try:
        # 连接到Milvus服务器
        connections.connect(host="localhost", port="19530")
        
        # 检查集合是否存在
        if utility.has_collection(collection_name):
            return Collection(name=collection_name)
        
        # 如果集合不存在，创建新集合
        vector_store = MilvusVectorStore(collection_name)
        collection =  vector_store.collection
        
        collection.load()
        
        return collection
        
    except Exception as e:
        raise Exception(f"初始化Milvus集合失败: {str(e)}")

# 处理Excel文件
def process_excel(file_path):
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        test_cases = []
        texts = []  # 用于存储向量化的文本
        
        for _, row in df.iterrows():
            # 构建用于向量化的文本
            text = (
                f"用例名称：{row['用例名称']}\n"
                f"ID：{row['ID']}\n"
                f"前置条件：{row['前置条件']}\n"
                f"所属模块：{row['所属模块']}\n"
                f"步骤描述：{row['步骤描述']}\n"
                f"预期结果：{row['预期结果']}\n"
                f"标签：{row['标签']}\n"
                f"备注：{row['备注']}\n"
                f"用例等级：{row['用例等级']}\n"
                f"执行结果：{row['执行结果']}\n"
                f"评审结果：{row['评审结果']}\n"
                f"创建人：{row['创建人']}\n"
                f"创建时间：{row['创建时间']}\n"
                f"更新人：{row['更新人']}\n"
                f"更新时间：{row['更新时间']}\n"
                f"用例评论：{row['用例评论']}\n"
                f"执行评论：{row['执行评论']}\n"
                f"评审评论：{row['评审评论']}\n"
                f"编辑模式：{row['编辑模式']}"
            )
            
            # 只有当关键字段不为空时才添加
            if row['用例名称'] and row['步骤描述'] and row['预期结果']:
                test_cases.append(row)  # 保存原始行数据
                texts.append(text.strip())  # 保存用于向量化的文本
        
        return test_cases, texts  # 返回原始数据和文本
    except KeyError as e:
        raise ValueError(f"Excel文件缺少必要的列: {str(e)}")
    except Exception as e:
        raise ValueError(f"Excel解析失败: {str(e)}")