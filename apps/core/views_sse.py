"""
SSE (Server-Sent Events) 流式日志传输视图

提供基于 Server-Sent Events 的实时日志推送功能，用于前端实时显示任务执行日志。
通过队列机制实现生产者-消费者模式，支持多任务并发。

主要功能：
- 接收 task_id 参数，建立 SSE 连接
- 从任务队列中实时拉取日志消息
- 发送心跳包防止连接超时
- 支持 JSON 格式的日志数据传输

使用场景：
- 测试用例生成过程中的实时日志显示
- 长时间运行任务的进度监控
- 前端实时更新任务状态
"""

import json
import time
from typing import Iterator
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from apps.agents.sse_bus import get_queue


@csrf_exempt
def stream_logs(request):
    task_id = request.GET.get("task_id")
    if not task_id:
        return StreamingHttpResponse(b"missing task_id", status=400)

    # 同步获取队列
    q, _ = get_queue(task_id)

    def event_stream() -> Iterator[bytes]:
        # 先发一行注释，帮助一些代理尽快刷出头部
        yield b": stream-start\n\n"
        while True:
            # 从同步队列拉取一条；带超时以便发送心跳
            try:
                item = q.get(timeout=15.0)
            except Exception:
                item = None
            if item is None:
                # 周期性发送进度事件，驱动前端刷新（替代注释心跳）
                payload = json.dumps({
                    "ts": int(time.time())
                }, ensure_ascii=False).encode("utf-8")
                yield b"event: progress\n"
                yield b"data: " + payload + b"\n\n"
                continue

            # 处理 Pydantic 模型
            if hasattr(item, 'dict'):
                item_dict = item.dict()
            else:
                item_dict = item
                
            data = json.dumps(item_dict, ensure_ascii=False).encode("utf-8")
            yield b"id: %d\n" % item_dict["seq"]
            yield b"event: log\n"
            yield b"data: " + data + b"\n\n"

    resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


