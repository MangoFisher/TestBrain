import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class KnowledgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.knowledge"

    embedder = None
    vector_store = None

    def ready(self):
        # 知识库依赖外部服务：Milvus 向量库 + 嵌入模型（阿里云 API 或本地 BGE-M3）。
        # 首次在本地启动时这些依赖通常还不具备，因此：
        #   1) 未开启 ENABLE_MILVUS 时直接跳过，保证项目能正常启动；
        #   2) 开启后若初始化失败，也只记录告警，不阻断 Django 启动。
        if not getattr(settings, "ENABLE_MILVUS", False):
            logger.info("ENABLE_MILVUS 未开启，跳过知识库（Milvus/嵌入模型）初始化")
            return

        try:
            from .embedding import create_embedder
            from .vector_store import MilvusVectorStore

            if KnowledgeConfig.embedder is None:
                KnowledgeConfig.embedder = create_embedder()
            if KnowledgeConfig.vector_store is None:
                KnowledgeConfig.vector_store = MilvusVectorStore()
        except Exception as e:
            logger.warning(f"知识库初始化失败，知识库相关功能暂不可用: {e}")