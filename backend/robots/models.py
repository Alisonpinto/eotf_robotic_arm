from enum import Enum
from typing import List, Optional
try:
    from pydantic import BaseModel, Field
except ImportError:
    try:
        from ai.schemas import BaseModel, Field
    except ImportError:
        from ..ai.schemas import BaseModel, Field
import time


class RobotOperatingMode(str, Enum):
    IDLE = "IDLE"
    MANUAL = "MANUAL"
    RUNNING_TASK = "RUNNING_TASK"
    ESTOP = "ESTOP"
    ERROR = "ERROR"


class ConnectionState(str, Enum):
    SIMULATED = "SIMULATED"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class JointAngles(BaseModel):
    """6-DOF Joint angles in degrees."""
    j1: float = Field(0.0, description="Joint 1 (Base Rotation): -180 to 180 deg")
    j2: float = Field(0.0, description="Joint 2 (Shoulder): -90 to 90 deg")
    j3: float = Field(0.0, description="Joint 3 (Elbow): -135 to 135 deg")
    j4: float = Field(0.0, description="Joint 4 (Wrist Pitch): -90 to 90 deg")
    j5: float = Field(0.0, description="Joint 5 (Wrist Roll): -180 to 180 deg")
    j6: float = Field(0.0, description="Joint 6 (Wrist Yaw/Tool): -180 to 180 deg")

    def to_list(self) -> List[float]:
        return [self.j1, self.j2, self.j3, self.j4, self.j5, self.j6]

    @classmethod
    def from_list(cls, angles: List[float]) -> "JointAngles":
        return cls(
            j1=angles[0] if len(angles) > 0 else 0.0,
            j2=angles[1] if len(angles) > 1 else 0.0,
            j3=angles[2] if len(angles) > 2 else 0.0,
            j4=angles[3] if len(angles) > 3 else 0.0,
            j5=angles[4] if len(angles) > 4 else 0.0,
            j6=angles[5] if len(angles) > 5 else 0.0,
        )


class Pose3D(BaseModel):
    """End-effector Cartesian coordinates and orientation."""
    x: float = Field(0.0, description="X Position in mm")
    y: float = Field(200.0, description="Y Position in mm")
    z: float = Field(150.0, description="Z Position in mm")
    roll: float = Field(0.0, description="Roll angle in degrees")
    pitch: float = Field(0.0, description="Pitch angle in degrees")
    yaw: float = Field(0.0, description="Yaw angle in degrees")


class GripperState(BaseModel):
    """Gripper actuation status."""
    position: float = Field(0.0, ge=0.0, le=100.0, description="0.0 = fully open, 100.0 = fully closed")
    state: str = Field("OPEN", description="OPEN, CLOSED, MOVING, or GRIPPING")


class RobotStatus(BaseModel):
    """Full telemetry status for a robotic arm."""
    id: str
    name: str
    arm_type: str = Field("6-DOF", description="Arm architecture description")
    connection: ConnectionState = ConnectionState.SIMULATED
    mode: RobotOperatingMode = RobotOperatingMode.IDLE
    joints: JointAngles = Field(default_factory=JointAngles)
    pose: Pose3D = Field(default_factory=Pose3D)
    gripper: GripperState = Field(default_factory=GripperState)
    voltage: float = Field(12.0, description="Bus voltage in Volts")
    temperature: float = Field(32.5, description="Average servo temperature in Celsius")
    current_load_pct: float = Field(8.0, description="Average motor load percentage")
    error_message: Optional[str] = None
    updated_at: float = Field(default_factory=time.time)


class MoveJointsRequest(BaseModel):
    joints: JointAngles
    speed: float = Field(1.0, ge=0.1, le=5.0, description="Speed multiplier")


class MovePoseRequest(BaseModel):
    pose: Pose3D
    speed: float = Field(1.0, ge=0.1, le=5.0, description="Speed multiplier")


class GripperRequest(BaseModel):
    position: float = Field(..., ge=0.0, le=100.0, description="0=open, 100=closed")
