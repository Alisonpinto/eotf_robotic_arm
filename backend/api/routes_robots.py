from fastapi import APIRouter, HTTPException
from typing import List

try:
    from robots.manager import robot_manager
    from robots.models import (
        RobotStatus,
        MoveJointsRequest,
        MovePoseRequest,
        GripperRequest,
    )
except ImportError:
    from ..robots.manager import robot_manager
    from ..robots.models import (
        RobotStatus,
        MoveJointsRequest,
        MovePoseRequest,
        GripperRequest,
    )

router = APIRouter(prefix="/api/robots", tags=["robots"])


@router.get("", response_model=List[RobotStatus])
async def list_robots():
    """Retrieve telemetry status for all registered robotic arms."""
    return robot_manager.get_all_statuses()


@router.get("/{robot_id}", response_model=RobotStatus)
async def get_robot_status(robot_id: str):
    """Retrieve telemetry status for a specific robot ('diy_arm' or 'jetarm')."""
    robot = robot_manager.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return robot.get_status()


@router.post("/{robot_id}/joints")
async def move_joints(robot_id: str, req: MoveJointsRequest):
    """Command target 6-DOF joint angles in degrees."""
    robot = robot_manager.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    success = await robot.move_joints(req.joints, speed=req.speed)
    return {"status": "ok" if success else "failed", "robot_id": robot_id}


@router.post("/{robot_id}/pose")
async def move_pose(robot_id: str, req: MovePoseRequest):
    """Command target end-effector 3D Cartesian coordinates and orientation."""
    robot = robot_manager.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    success = await robot.move_pose(req.pose, speed=req.speed)
    return {"status": "ok" if success else "failed", "robot_id": robot_id}


@router.post("/{robot_id}/gripper")
async def set_gripper(robot_id: str, req: GripperRequest):
    """Actuate gripper (0.0=open, 100.0=closed)."""
    robot = robot_manager.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    success = await robot.set_gripper(req.position)
    return {"status": "ok" if success else "failed", "robot_id": robot_id, "position": req.position}


@router.post("/{robot_id}/home")
async def home_robot(robot_id: str):
    """Move robot arm to home calibration pose."""
    robot = robot_manager.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    success = await robot.home()
    return {"status": "ok" if success else "failed", "robot_id": robot_id}


@router.post("/{robot_id}/estop")
async def emergency_stop_robot(robot_id: str):
    """Halt motor movement for specified robot."""
    robot = robot_manager.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    success = await robot.emergency_stop()
    return {"status": "estop_active", "robot_id": robot_id}


@router.post("/system/estop_all")
async def emergency_stop_all():
    """Emergency stop all robotic arms across the platform."""
    results = await robot_manager.emergency_stop_all()
    return {"status": "all_arms_estopped", "details": results}


@router.post("/system/home_all")
async def home_all():
    """Home all robotic arms simultaneously."""
    results = await robot_manager.home_all()
    return {"status": "all_arms_homed", "details": results}
