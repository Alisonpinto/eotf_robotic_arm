import asyncio
import time
from typing import Dict, List, Optional
from .models import TaskRecord, TaskState, TaskLogEntry, LogLevel

try:
    from ai.schemas import ActionPlan, ActionType, RobotAction
    from robots.manager import robot_manager
    from robots.models import JointAngles, Pose3D
except ImportError:
    from ..ai.schemas import ActionPlan, ActionType, RobotAction
    from ..robots.manager import robot_manager
    from ..robots.models import JointAngles, Pose3D


class TaskManager:
    """
    Orchestrates asynchronous execution of AI Action Plans across robotic arms.
    Maintains active task state, progress percentage, step transitions, and real-time logs.
    """

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}
        self._active_task_id: Optional[str] = None
        self._running_async_tasks: Dict[str, asyncio.Task] = {}

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> List[TaskRecord]:
        tasks = list(self._tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def get_active_task(self) -> Optional[TaskRecord]:
        if self._active_task_id:
            return self._tasks.get(self._active_task_id)
        return None

    def create_task(self, plan: ActionPlan) -> TaskRecord:
        record = TaskRecord(
            plan=plan,
            structured_task=plan.structured_task,
            total_steps=len(plan.actions),
            current_step_desc=f"Queued plan: {plan.intent}"
        )
        self._add_log(record, LogLevel.INFO, f"Task created: '{plan.raw_command}' ({len(plan.actions)} steps)")
        self._tasks[record.task_id] = record
        return record

    def start_task(self, task_id: str) -> bool:
        record = self._tasks.get(task_id)
        if not record or record.state not in (TaskState.PENDING,):
            return False

        self._active_task_id = task_id
        async_task = asyncio.create_task(self._execute_task_workflow(record))
        self._running_async_tasks[task_id] = async_task
        return True

    def cancel_task(self, task_id: str) -> bool:
        record = self._tasks.get(task_id)
        if not record:
            return False

        if task_id in self._running_async_tasks:
            self._running_async_tasks[task_id].cancel()

        record.state = TaskState.CANCELLED
        record.completed_at = time.time()
        self._add_log(record, LogLevel.WARN, "Task was cancelled by operator.")
        if self._active_task_id == task_id:
            self._active_task_id = None
        return True

    def _add_log(self, record: TaskRecord, level: LogLevel, message: str):
        record.logs.append(TaskLogEntry(
            timestamp=time.time(),
            formatted_time=time.strftime("%H:%M:%S"),
            level=level,
            message=message
        ))

    async def _execute_task_workflow(self, record: TaskRecord):
        record.state = TaskState.RUNNING
        record.started_at = time.time()
        self._add_log(record, LogLevel.INFO, f"Executing intent [{record.plan.intent}] on target [{record.plan.target_robot}]")

        try:
            total = max(1, record.total_steps)

            for idx, action in enumerate(record.plan.actions):
                record.current_step_index = idx + 1
                record.current_step_desc = action.description
                record.progress_pct = round(((idx) / total) * 100.0, 1)

                self._add_log(
                    record,
                    LogLevel.STEP,
                    f"Step {idx + 1}/{total}: {action.description} [{action.robot_id}]"
                )

                # Execute action on target robot(s)
                success = await self._dispatch_action(action)
                if not success:
                    raise RuntimeError(f"Action execution failed: {action.description}")

                # Update progress after step completion
                record.progress_pct = round(((idx + 1) / total) * 100.0, 1)

            record.state = TaskState.COMPLETED
            record.completed_at = time.time()
            record.progress_pct = 100.0
            record.current_step_desc = "Task finished successfully"
            self._add_log(record, LogLevel.SUCCESS, "All plan actions completed successfully.")

        except asyncio.CancelledError:
            record.state = TaskState.CANCELLED
            record.completed_at = time.time()
            self._add_log(record, LogLevel.WARN, "Execution interrupted (task cancelled).")
        except Exception as e:
            record.state = TaskState.FAILED
            record.error = str(e)
            record.completed_at = time.time()
            self._add_log(record, LogLevel.ERROR, f"Execution failed: {str(e)}")
        finally:
            if self._active_task_id == record.task_id:
                self._active_task_id = None
            if record.task_id in self._running_async_tasks:
                del self._running_async_tasks[record.task_id]

    async def _dispatch_action(self, action: RobotAction) -> bool:
        target_ids = ["diy_arm", "jetarm"] if action.robot_id == "both" else [action.robot_id]

        for robot_id in target_ids:
            robot = robot_manager.get_robot(robot_id)
            if not robot:
                robot = robot_manager.get_robot("jetarm")
                if not robot:
                    return False

            if action.action_type == ActionType.HOME:
                await robot.home()

            elif action.action_type == ActionType.EMERGENCY_STOP:
                await robot.emergency_stop()

            elif action.action_type == ActionType.SET_GRIPPER:
                pos = float(action.parameters.get("position", 0.0))
                await robot.set_gripper(pos)

            elif action.action_type == ActionType.MOVE_JOINTS:
                angles_raw = action.parameters.get("joints", [0.0]*6)
                if isinstance(angles_raw, list):
                    angles = JointAngles.from_list(angles_raw)
                else:
                    angles = JointAngles(**angles_raw)
                await robot.move_joints(angles, speed=1.2)

            elif action.action_type == ActionType.MOVE_POSE:
                p = action.parameters
                pose = Pose3D(
                    x=float(p.get("x", 0.0)),
                    y=float(p.get("y", 200.0)),
                    z=float(p.get("z", 100.0)),
                    roll=float(p.get("roll", 0.0)),
                    pitch=float(p.get("pitch", 0.0)),
                    yaw=float(p.get("yaw", 0.0)),
                )
                await robot.move_pose(pose, speed=1.2)

            elif action.action_type == ActionType.WAIT:
                secs = float(action.parameters.get("seconds", 0.5))
                await asyncio.sleep(secs)

            elif action.action_type == ActionType.DETECT_OBJECT:
                await asyncio.sleep(0.6)

        return True


# Singleton task manager
task_manager = TaskManager()
