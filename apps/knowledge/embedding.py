import requests
import numpy as np
from typing import List, Union, Dict

class BGEM3Embedder:
    """BGE-M3嵌入模型服务"""
    
    def __init__(self, api_key: str = None, api_url: str = None):
        self.api_key = api_key
        self.api_url = api_url or "https://api-inference.huggingface.co/models/BAAI/bge-m3"
        
    def get_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """获取文本的嵌入向量"""
        if isinstance(texts, str):
            texts = [texts]
            
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        response = requests.post(
            self.api_url,
            headers=headers,
            json={"inputs": texts}
        )
        response.raise_for_status()
        
        embeddings = response.json()
        return embeddings 