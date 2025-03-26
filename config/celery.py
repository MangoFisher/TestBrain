import os
from celery import Celery
import billiard as multiprocessing

# 只在尚未设置时设置启动方法
if not multiprocessing.get_start_method(allow_none=True):
    multiprocessing.set_start_method('spawn')

# 设置 Django 默认配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 创建 Celery 实例
app = Celery('config')

# 使用 Django 的配置文件配置 Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery 配置更新
app.conf.update(
    worker_max_tasks_per_child=1,     # 每个 worker 只处理一个任务
    worker_prefetch_multiplier=1,     # 限制任务预取
    task_time_limit=3600,            # 任务超时时间：1小时
    broker_connection_retry_on_startup=True,  # 启动时重试连接
    worker_concurrency=1,            # 限制并发数为1
    task_acks_late=True,             # 任务完成后再确认
    task_reject_on_worker_lost=True  # worker 丢失时拒绝任务
)

# 自动发现任务
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 