from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import time
import uuid
try:
    from ai.schemas import ActionPlan, StructuredTask
except ImportError:
    from ..ai.schemas import ActionPlan, StructuredTask


class TaskState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class LogLevel(str, Enum):
    INFO = "INFO"
    STEP = "STEP"
    SUCCESS = "SUCCESS"
    WARN = "WARN"
    ERROR = "ERROR"


class TaskLogEntry(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    formatted_time: str = Field(default_factory=lambda: time.strftime("%H:%M:%S"))
    level: LogLevel = LogLevel.INFO
    message: str


class TaskRecord(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{str(uuid.uuid4())[:8]}")
    plan: ActionPlan
    structured_task: Optional[StructuredTask] = None
    state: TaskState = TaskState.PENDING
    progress_pct: float = 0.0
    current_step_index: int = 0
    total_steps: int = 0
    current_step_desc: str = "Initialized"
    logs: List[TaskLogEntry] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
