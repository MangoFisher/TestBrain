from django.apps import AppConfig

class KnowledgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.knowledge"

    embedder = None
    vector_store = None

    def ready(self):
        from .embedding import BGEM3Embedder
        from .vector_store import MilvusVectorStore

        if KnowledgeConfig.embedder is None:
            KnowledgeConfig.embedder = BGEM3Embedder()
        if KnowledgeConfig.vector_store is None:
            KnowledgeConfig.vector_store = MilvusVectorStore()