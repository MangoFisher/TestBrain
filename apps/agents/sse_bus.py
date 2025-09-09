"""
SSE 日志总线

提供任务日志的队列管理和发布功能，支持 SSE 流式传输。
每个任务维护独立的队列和序号，实现生产者-消费者模式。

全局变量：
- _task_bus: 任务队列字典 {task_id: (queue, seq)}
- _bus_lock: 线程安全锁
"""

import time
from typing import Dict, Tuple, Any
from queue import Queue, Empty
from threading import Lock
from .schemas.progress_schema import SSELogEntry, LogLevel

# 内存版任务日志总线：每个 task_id 一个队列和递增序号（同步队列）
_task_bus: Dict[str, Tuple[Queue, int]] = {}
_bus_lock = Lock()


def get_queue(task_id: str) -> Tuple[Queue, int]:
    """获取任务的队列和序号，不存在则创建新的"""
    with _bus_lock:
        if task_id in _task_bus:
            return _task_bus[task_id]
        q: Queue = Queue(maxsize=1000)
        _task_bus[task_id] = (q, 0)
        return _task_bus[task_id]


def publish_log(task_id: str, level: str, msg: str, name: str = "", thread: str = "", task_type: str = "generation", module: str = "") -> None:
    """发布日志到任务队列，支持背压控制（队列满时丢弃最旧消息）"""
    q, seq = get_queue(task_id)
    seq += 1
    # 更新 seq
    with _bus_lock:
        _task_bus[task_id] = (q, seq)
    # 使用 Pydantic 模型创建日志条目
    try:
        # 验证日志级别
        log_level = LogLevel(level) if level in [e.value for e in LogLevel] else LogLevel.INFO
    except ValueError:
        log_level = LogLevel.INFO
    
    # 规范化任务类型
    try:
        tt = SSELogEntry.TaskType(task_type)
    except Exception:
        tt = SSELogEntry.TaskType.GENERATION

    item = SSELogEntry(
        seq=seq,
        ts=time.time(),
        task_id=task_id,
        level=log_level,
        name=name,
        thread=thread,
        msg=msg,
        task_type=tt,
        module=module or name,
    )
    # 背压：满则丢最旧
    if q.full():
        try:
            q.get_nowait() # 移除并返回队列头部的元素（最旧的）
        except Empty:
            pass
    try:
        q.put_nowait(item)
    except Exception:
        # 队列满且竞争条件下 put 失败，忽略
        pass


