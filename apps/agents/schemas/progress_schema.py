from typing import List, Optional, Union
from pydantic import BaseModel, Field
import time


class ProgressData(BaseModel):
    """任务进度数据模型"""
    
    # 基本进度信息
    step: Optional[int] = Field(None, description="当前步骤编号")
    message: Optional[str] = Field(None, description="当前步骤描述")
    percentage: Optional[float] = Field(None, ge=0, le=100, description="完成百分比 (0-100)")
    
    # 接口相关
    current_api: Optional[str] = Field(None, description="当前正在处理的接口名称")
    total_apis: Optional[int] = Field(None, ge=0, description="总接口数量")
    completed_apis: Optional[int] = Field(None, ge=0, description="已完成接口数量")
    
    # 文件相关
    file_path: Optional[str] = Field(None, description="生成的文件路径")
    
    # 日志相关
    logs: List[str] = Field(default_factory=list, description="日志列表")
    
    # 时间戳
    timestamp: float = Field(default_factory=time.time, description="最后更新时间戳")
    
    # 其他扩展字段
    extra: dict = Field(default_factory=dict, description="其他扩展数据")
    
    class Config:
        # 允许额外字段
        extra = "allow"
        # 验证赋值
        validate_assignment = True


class ProgressUpdate(BaseModel):
    """进度更新数据模型（用于 set_progress 函数）"""
    
    # 基本进度信息
    step: Optional[int] = None
    message: Optional[str] = None
    percentage: Optional[float] = Field(None, ge=0, le=100)
    
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
