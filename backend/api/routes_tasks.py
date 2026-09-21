from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

try:
    from tasks.task_manager import task_manager
    from tasks.models import TaskRecord
except ImportError:
    from ..tasks.task_manager import task_manager
    from ..tasks.models import TaskRecord

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskRecord])
async def get_recent_tasks(limit: int = Query(20, ge=1, le=100)):
    """Retrieve history of recently executed or pending tasks."""
    return task_manager.list_tasks(limit=limit)


@router.get("/active", response_model=Optional[TaskRecord])
async def get_active_task():
    """Retrieve the currently executing task, if any."""
    return task_manager.get_active_task()


@router.get("/{task_id}", response_model=TaskRecord)
async def get_task_by_id(task_id: str):
    """Retrieve full progress status and real-time step logs for a task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a pending or running task."""
    success = task_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task '{task_id}'")
    return {"status": "cancelled", "task_id": task_id}
