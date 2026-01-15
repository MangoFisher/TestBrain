"""
进度跟踪数据模型定义

本模块定义了用于任务进度跟踪的 Pydantic 数据模型，支持：
1. 任务进度信息（步骤、消息、百分比）
2. 接口处理状态（当前接口、总数、已完成数）
3. 文件生成信息（文件路径）
4. 实时日志收集（日志列表）
5. 扩展字段支持

主要用途：
- 在 progress_registry.py 中存储任务进度数据
- 在 SSE 流式传输中序列化进度信息
- 在前端轮询 API 中返回结构化进度数据
- 提供类型安全和数据验证

数据流向：
1. 业务逻辑调用 set_progress(task_id, ProgressUpdate)
2. progress_registry 将 ProgressUpdate 合并到 ProgressData
3. SSE/轮询 API 返回 ProgressData 给前端
4. 前端解析并更新 UI 显示
"""

from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field
from enum import Enum
import time


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SSELogEntry(BaseModel):
    """SSE 日志条目数据模型"""
    seq: int = Field(ge=1, description="日志序号")
    ts: float = Field(ge=0, description="时间戳")
    task_id: str = Field(min_length=1, description="任务ID")
    level: LogLevel = Field(description="日志级别")
    name: str = Field(default="", description="日志来源名称")
    thread: str = Field(default="", description="线程名")
    msg: str = Field(description="日志消息内容")
    # 扩展：任务类型与模块名，支持多任务并行分类展示
    class TaskType(str, Enum):
        GENERATION = "generation"
        REVIEW = "review"
        ANALYSIS = "analysis"
        OTHER = "other"

    task_type: TaskType = Field(default=TaskType.GENERATION, description="任务类型")
    module: str = Field(default="", description="业务模块名")
    
    class Config:
        validate_assignment = True


class ProgressData(BaseModel):
    """任务进度数据模型"""
    
    # 基本进度信息
    step: Optional[int] = Field(None, ge=0, description="当前步骤编号")
    message: Optional[str] = Field(None, description="当前步骤描述")
    percentage: Optional[float] = Field(None, ge=0, le=100, description="完成百分比 (0-100)")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    
    # 接口相关
    current_api: Optional[str] = Field(None, description="当前正在处理的接口名称")
    total_apis: Optional[int] = Field(None, ge=0, description="总接口数量")
    completed_apis: Optional[int] = Field(None, ge=0, description="已完成接口数量")
    
    # 文件相关
    file_path: Optional[str] = Field(None, description="生成的文件路径")
    
    # 日志相关
    logs: List[str] = Field(default_factory=list, max_items=2000, description="日志列表")
    
    # 时间戳
    timestamp: float = Field(default_factory=time.time, description="最后更新时间戳")
    created_at: float = Field(default_factory=time.time, description="任务创建时间戳")
    
    # 其他扩展字段
    extra: dict = Field(default_factory=dict, description="其他扩展数据")
    
    class Config:
        # 使用别名减少 JSON 大小
        allow_population_by_field_name = True
        # 优化序列化性能
        json_encoders = {
            time: lambda v: v,
        }
        # 验证赋值
        validate_assignment = True
        # 允许额外字段
        extra = "allow"


class ProgressUpdate(BaseModel):
    """进度更新数据模型（用于 set_progress 函数）"""
    
    # 基本进度信息
    step: Optional[int] = Field(None, ge=0)
    message: Optional[str] = None
    percentage: Optional[float] = Field(None, ge=0, le=100)
    status: Optional[TaskStatus] = None
    
    # 接口相关
    current_api: Optional[str] = None
    total_apis: Optional[int] = Field(None, ge=0)
    completed_apis: Optional[int] = Field(None, ge=0)
    
    # 文件相关
    file_path: Optional[str] = None
    
    # 日志相关（特殊处理）
    log: Optional[Union[str, List[str]]] = Field(None, description="要追加的日志")
    
    # 其他扩展字段
    extra: Optional[dict] = None
    
    class Config:
        # 允许额外字段
        extra = "allow"
