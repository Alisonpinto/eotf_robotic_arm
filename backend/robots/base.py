from abc import ABC, abstractmethod
from typing import Optional
from .models import RobotStatus, JointAngles, Pose3D, GripperState


class RobotArmInterface(ABC):
    """
    Abstract Base Class for 6-DOF Robotic Arms.
    
    Any hardware driver (DIY 3D-printed arm with Arduino/ESP32, Hiwonder JetArm SDK,
    ROS2 controller, or digital twin simulation) must implement this interface.
    This ensures the upper layers (AI interpreter, Task Manager, Web Dashboard)
    never depend on specific physical hardware.
    """

    @abstractmethod
    def get_id(self) -> str:
        """Return unique identifier for this robot (e.g. 'diy_arm', 'jetarm')."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable display name."""
        pass

    @abstractmethod
    def get_status(self) -> RobotStatus:
        """Return latest telemetry snapshot."""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to robot or initialize simulation driver."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect and release control handles safely."""
        pass

    @abstractmethod
    async def emergency_stop(self) -> bool:
        """Halt all motor movements immediately and enter ESTOP mode."""
        pass

    @abstractmethod
    async def home(self) -> bool:
        """Move all joints to designated home/calibration position."""
        pass

    @abstractmethod
    async def move_joints(self, target: JointAngles, speed: float = 1.0) -> bool:
        """Command joint space movement to target angles."""
        pass

    @abstractmethod
    async def move_pose(self, target: Pose3D, speed: float = 1.0) -> bool:
        """Command Cartesian space movement to target end-effector pose."""
        pass

    @abstractmethod
    async def set_gripper(self, position: float) -> bool:
        """
        Actuate the end-effector gripper.
        :param position: 0.0 (fully open) to 100.0 (fully closed).
        """
        pass
