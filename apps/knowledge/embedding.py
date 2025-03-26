import torch
from typing import List, Union, Dict
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

import numpy as np
import os

class BGEM3Embedder:
    """BGE-M3嵌入模型本地服务"""
    _instance = None
    _model = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式，确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = 'cpu'):
        """初始化模型，使用单例模式避免重复加载"""
        if self._model is None:
            try:
                print("正在加载BGE-M3模型...")
                # 强制使用 CPU
                os.environ['CUDA_VISIBLE_DEVICES'] = ''
                os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '0'
                
                from sentence_transformers import SentenceTransformer
                import torch
                torch.device('cpu')  # 强制使用 CPU
                
                # 设置模型缓存目录
                cache_dir = os.path.join(os.path.dirname(__file__), 'model_cache')
                os.makedirs(cache_dir, exist_ok=True)
                
                self._model = SentenceTransformer(
                    model_name,
                    cache_folder=cache_dir,
                    device='cpu'  # 强制使用 CPU
                )
                print("BGE-M3模型加载完成")
            except Exception as e:
                print(f"BGE-M3模型加载失败: {str(e)}")
                raise

    def get_embeddings(self, texts: Union[str, List[str]], show_progress_bar: bool = False) -> List[List[float]]:
        """获取文本的嵌入向量"""
        if isinstance(texts, str):
            texts = [texts]
        embeddings = self._model.encode(sentences=texts, normalize_embeddings=True, show_progress_bar=show_progress_bar)
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