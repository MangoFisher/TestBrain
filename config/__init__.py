# 空文件，使config成为一个Python包 

# 确保在 Django 启动时加载 Celery
from .celery import app as celery_app

__all__ = ('celery_app',) 