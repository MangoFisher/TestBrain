# 空文件，使config成为一个Python包 

from .celery import app as celery_app

__all__ = ('celery_app',) 