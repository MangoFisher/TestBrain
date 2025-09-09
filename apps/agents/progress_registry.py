"""
任务进度注册表

提供线程安全的任务进度数据存储和管理功能，支持多任务并发执行时的进度跟踪。

主要功能：
- 存储和更新任务进度数据（步骤、百分比、消息等）
- 收集和追加任务执行日志
- 提供进度数据查询和清理接口
- 支持任务过期清理机制

核心特性：
- 线程安全：使用锁保护共享数据
- 类型安全：基于 Pydantic 模型进行数据验证
- 日志管理：自动限制日志数量，防止内存溢出
- 时间戳：自动记录最后更新时间

使用场景：
- 测试用例生成任务的进度跟踪
- 长时间运行任务的状态监控
- 前端实时进度显示的数据源
"""

import threading
import time
from typing import Dict, Optional
from .schemas.progress_schema import ProgressData, ProgressUpdate, TaskStatus

_progress_registry: Dict[str, ProgressData] = {}
_lock = threading.Lock()


def set_progress(task_id: str, data: dict) -> None:
    """合并任务进度数据，如果提供了日志则追加到日志列表。

    使用标准化的 ProgressData 模型进行类型验证和数据管理。
    """
    with _lock:
        # 获取当前进度数据，如果不存在则创建新的
        current = _progress_registry.get(task_id)
        if current is None:
            current = ProgressData()
        
        # 解析更新数据
        try:
            update_data = ProgressUpdate(**data)
        except Exception as e:
            # 如果解析失败，回退到原始逻辑
            current_dict = current.dict()
            current_dict.update(data)
            current_dict['timestamp'] = time.time()
            _progress_registry[task_id] = ProgressData(**current_dict)
            return
        
        # 处理日志追加
        if update_data.log is not None:
            if isinstance(update_data.log, list):
                current.logs.extend([str(x) for x in update_data.log])
            else:
                current.logs.append(str(update_data.log))
            # 限制日志长度
            current.logs = current.logs[-2000:]
        
        # 更新其他字段
        update_dict = update_data.dict(exclude={'log'}, exclude_none=True)
        for key, value in update_dict.items():
            if hasattr(current, key):
                setattr(current, key, value)
        
        # 自动更新任务状态
        if current.percentage is not None:
            if current.percentage >= 100:
                current.status = TaskStatus.COMPLETED
            elif current.percentage > 0:
                current.status = TaskStatus.RUNNING
        
        # 更新时间戳
        current.timestamp = time.time()
        
        # 保存更新后的数据
        _progress_registry[task_id] = current


def get_progress(task_id: str) -> Optional[ProgressData]:
    with _lock:
        return _progress_registry.get(task_id)


def clear_progress(task_id: str) -> None:
    with _lock:
        if task_id in _progress_registry:
            del _progress_registry[task_id]


def cleanup_expired(max_age_seconds: int = 3600) -> None:
    now = time.time()
    expired: Dict[str, ProgressData] = {}
    with _lock:
        for tid, prog in list(_progress_registry.items()):
            if now - prog.timestamp > max_age_seconds:
                expired[tid] = prog
                del _progress_registry[tid]

