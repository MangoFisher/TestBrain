import threading
import time
from typing import Dict, Any, Optional

_progress_registry: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def set_progress(task_id: str, data: Dict[str, Any]) -> None:
    with _lock:
        data.setdefault('timestamp', time.time())
        _progress_registry[task_id] = data


def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _progress_registry.get(task_id)


def clear_progress(task_id: str) -> None:
    with _lock:
        if task_id in _progress_registry:
            del _progress_registry[task_id]


def cleanup_expired(max_age_seconds: int = 3600) -> None:
    now = time.time()
    expired: Dict[str, Dict[str, Any]] = {}
    with _lock:
        for tid, prog in list(_progress_registry.items()):
            ts = prog.get('timestamp', 0)
            if now - ts > max_age_seconds:
                expired[tid] = prog
                del _progress_registry[tid]

