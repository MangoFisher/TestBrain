import torch
from typing import List, Union, Dict
# from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

import numpy as np
import os

class BGEM3Embedder:
    """BGE-M3嵌入模型本地服务 - 针对Apple Silicon优化"""
    
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """
        初始化BGE-M3嵌入模型
        
        Args:
            model_name: 模型名称，默认为'BAAI/bge-m3'
        """
        print("正在加载BGE-M3模型...")
        self.model = SentenceTransformer(model_name)

        
    def get_embeddings(self, texts: Union[str, List[str]], show_progress_bar: bool = False) -> List[List[float]]:
        """获取文本的嵌入向量"""
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self.model.encode(sentences=texts, normalize_embeddings=True, show_progress_bar=show_progress_bar)
        return embeddings.tolist()
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本之间的相似度"""
        embeddings = self.get_embeddings([text1, text2])
        similarity = np.dot(embeddings[0], embeddings[1])
        return similarity

# 测试
if __name__ == "__main__":
    # 设置环境变量以优化MPS性能
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    
    # 初始化嵌入模型
    print("初始化BGE-M3嵌入模型...")
    embedder = BGEM3Embedder()
    
    # 测试单个文本
    print("\n测试单个文本嵌入...")
    text = "BGE-M3是一个强大的多语言嵌入模型"
    embedding = embedder.get_embeddings(text)
    print(f"嵌入维度: {len(embedding[0])}")
    print(f"前5个维度: {embedding[0][:5]}")
    
    # 测试多个文本
    print("\n测试多个文本嵌入...")
    texts = ["你好，世界", "Hello, world", "BGE-M3支持多种语言"]
    embeddings = embedder.get_embeddings(texts)
    print(f"嵌入数量: {len(embeddings)}")
    print(f"嵌入维度: {len(embeddings[0])}")
    
    # 测试相似度计算
    print("\n测试文本相似度...")
    text1 = "我喜欢人工智能技术"
    text2 = "AI技术非常有趣"
    text3 = "今天天气真不错"
    
    sim1 = embedder.compute_similarity(text1, text2)
    sim2 = embedder.compute_similarity(text1, text3)
    
    print(f"相似文本的相似度: {sim1:.4f}")
    print(f"不相似文本的相似度: {sim2:.4f}")
    
    # 测试批处理性能
    print("\n测试批处理性能...")
    import time
    batch_texts = ["测试文本" + str(i) for i in range(10)]
    
    start_time = time.time()
    batch_embeddings = embedder.get_embeddings(batch_texts)
    end_time = time.time()
    
    print(f"处理10个文本耗时: {end_time - start_time:.2f}秒")