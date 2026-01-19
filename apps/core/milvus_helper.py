"""
Milvus 向量数据库操作助手
"""

import pandas as pd
from pymilvus import connections, Collection, DataType, utility, FieldSchema, CollectionSchema
from sentence_transformers import SentenceTransformer
from apps.knowledge.vector_store import MilvusVectorStore

from unstructured.partition.xlsx import partition_xlsx
# chunking策略basic适合表格结构文件, by_title适合文档结构文件,具体可翻阅https://docs.unstructured.io/open-source/core-functionality/chunking
from unstructured.chunking.basic import chunk_elements
from unstructured.chunking.title import chunk_by_title
from apps.utils.logger_manager import get_logger
from unstructured.partition.auto import partition
import os


logger = get_logger(__name__)    

# 初始化嵌入模型（单例模式）
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True)
    return _embedding_model

# 初始化Milvus集合
def init_milvus_collection(collection_name="vv_knowledge_collection"):
    """初始化Milvus集合"""
    logger.info("进入到init_milvus_collection方法")
    try:
        # 连接到Milvus服务器
        connections.connect(host="localhost", port="19530")
        
        # 检查集合是否存在
        if utility.has_collection(collection_name):
            return Collection(name=collection_name)
        
        # 如果集合不存在，创建新集合
        vector_store = MilvusVectorStore(collection_name=collection_name)
        # 由于MilvusVectorStore类内部已经处理了集合创建，我们直接连接到已创建的集合
        collection = Collection(name=collection_name)
        collection.load()
        
        return collection
        
    except Exception as e:
        raise Exception(f"初始化Milvus集合失败: {str(e)}")

# 处理单个Excel文件
def process_single_excel(file_path):
    """处理单个Excel文件"""
    try:
        elements = partition_xlsx(filename=file_path)
        chunks = chunk_elements(elements=elements, max_characters=500)
    except Exception as e:
        raise ValueError(f"Excel文件处理失败: {str(e)}")
    return chunks

# 处理单个pdf文件
def process_single_pdf(file_path):
    """处理单个pdf文件"""
    try:
        elements = partition(filename=file_path)
        chunks = chunk_by_title(
            elements,
            max_characters=500,         # 每个块最多1500个字符
            combine_text_under_n_chars=200,  # 合并小于300字符的块
            multipage_sections=True,     # 允许部分跨页
        )
    except Exception as e:
        raise ValueError(f"Excel文件处理失败: {str(e)}")
    return chunks


def process_singel_file(file_path):
    """处理单个文件, 返回文件分区、chunking后的chunks"""
    # NOTE: 如下是unstructured支持解析的文件类型，除此外的文件类型无法解析
    file_categories = {
        "CSV": [".csv"],
        "E-mail": [".eml", ".msg", ".p7s"],
        "EPUB": [".epub"],
        "Excel": [".xls", ".xlsx"],
        "HTML": [".html"],
        "Image": [".bmp", ".heic", ".jpeg", ".png", ".tiff"],
        "Markdown": [".md"],
        "Org Mode": [".org"],
        "Open Office": [".odt"],
        "PDF": [".pdf"],
        "Plain text": [".txt"],
        "PowerPoint": [".ppt", ".pptx"],
        "reStructured Text": [".rst"],
        "Rich Text": [".rtf"],
        "TSV": [".tsv"],
        "Word": [".doc", ".docx"],
        "XML": [".xml"]
    }
    file_type = os.path.splitext(file_path)[1]
    for _, types in file_categories.items():
        if file_type in types:
            #FIXME: 目前是自动判断文件类型，并根据文件类型使用对应的文件类型分区函数的默认参数，如果想更特性化的处理某一种文件类型，需要使用指定的文件分区函数 
            logger.info(f"开始解析文件: {file_path}")
            try:
                if file_type in [".xlsx", ".xls"]:
                    chunks = process_single_excel(file_path)
                elif file_type in [".pdf"]:
                    chunks = process_single_pdf(file_path)
                else:
                    elements = partition(filename=file_path)
                    chunks = chunk_by_title(elements=elements, max_characters=500)
                logger.info(f"文件调用unstructured库分区、chunking成功")
                return chunks
            except Exception as e:
                logger.error(f"文件调用unstructured库分区、chunking失败: {str(e)}")
                return None
    raise ValueError(f"不支持的文件类型: {file_type}")



