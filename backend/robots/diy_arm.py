import asyncio
import math
import random
import time
from typing import Optional
from .base import RobotArmInterface
from .models import (
    RobotStatus,
    JointAngles,
    Pose3D,
    GripperState,
    ConnectionState,
    RobotOperatingMode,
)


class DIYArmController(RobotArmInterface):
    """
    Controller for Custom DIY 3D-Printed 6-DOF Robotic Arm.
    
    Current Implementation:
      High-fidelity simulation mode with realistic joint motion interpolation,
      forward kinematics approximation, and simulated telemetry.
      
    Hardware Integration Hook:
      When physical hardware is ready:
      1. Set self._simulation = False
      2. In connect(), initialize serial connection (e.g., PySerial to Arduino/ESP32 /dev/ttyUSB0 or COM3)
      3. In move_joints(), transmit G-Code or binary servo packet over serial
      4. In set_gripper(), transmit servo PWM/angle command
    """

    def __init__(self, robot_id: str = "diy_arm", name: str = "DIY 3D-Printed Arm"):
        self.robot_id = robot_id
        self.name = name
        self._simulation = True

        # Telemetry state
        self._connection = ConnectionState.SIMULATED
        self._mode = RobotOperatingMode.IDLE
        self._joints = JointAngles(j1=0.0, j2=15.0, j3=45.0, j4=-30.0, j5=0.0, j6=0.0)
        self._gripper = GripperState(position=0.0, state="OPEN")
        self._voltage = 12.1
        self._temperature = 31.4
        self._current_load_pct = 6.5
        self._error_message: Optional[str] = None
        self._last_update = time.time()
        self._is_moving = False

        # Compute initial forward kinematics
        self._pose = self._calculate_fk(self._joints)

    def get_id(self) -> str:
        return self.robot_id

    def get_name(self) -> str:
        return self.name

    def _calculate_fk(self, joints: JointAngles) -> Pose3D:
        """
        Approximate forward kinematics for DIY 6-DOF arm geometry.
        Segment lengths: L1 (base-to-shoulder)=80mm, L2 (upper arm)=150mm, L3 (forearm)=140mm, L4 (wrist/gripper)=90mm.
        """
        j1_rad = math.radians(joints.j1)
        j2_rad = math.radians(joints.j2)
        j3_rad = math.radians(joints.j3)
        j4_rad = math.radians(joints.j4)

        # Simplified 2D reach in arm plane
        theta = j2_rad
        r = 150.0 * math.sin(theta)
        z = 80.0 + 150.0 * math.cos(theta)

        theta += j3_rad
        r += 140.0 * math.sin(theta)
        z += 140.0 * math.cos(theta)

        theta += j4_rad
        r += 90.0 * math.sin(theta)
        z += 90.0 * math.cos(theta)

        # Rotate by base joint j1
        x = r * math.sin(j1_rad)
        y = r * math.cos(j1_rad)

        return Pose3D(
            x=round(x, 1),
            y=round(y, 1),
            z=round(max(0.0, z), 1),
            roll=round(joints.j5, 1),
            pitch=round(joints.j4, 1),
            yaw=round(joints.j6, 1),
        )

    def get_status(self) -> RobotStatus:
        # Micro telemetry variation for realistic feel
        volt_jitter = round(random.uniform(-0.05, 0.05), 2)
        temp_jitter = round(random.uniform(-0.1, 0.1), 1)

        return RobotStatus(
            id=self.robot_id,
            name=self.name,
            arm_type="Custom 3D-Printed 6-DOF (Stepper/Servo Hybrid)",
            connection=self._connection,
            mode=self._mode,
            joints=self._joints,
            pose=self._pose,
            gripper=self._gripper,
            voltage=max(11.0, min(12.6, self._voltage + volt_jitter)),
            temperature=max(25.0, min(50.0, self._temperature + temp_jitter)),
            current_load_pct=round(18.0 if self._is_moving else 6.0 + random.uniform(-1, 1), 1),
            error_message=self._error_message,
            updated_at=time.time(),
        )

    async def connect(self) -> bool:
        if self._simulation:
            self._connection = ConnectionState.SIMULATED
            self._mode = RobotOperatingMode.IDLE
            return True
        # Hardware connection hook (e.g., serial.Serial("/dev/ttyUSB0", 115200))
        return False

    async def disconnect(self) -> bool:
        self._connection = ConnectionState.DISCONNECTED
        self._mode = RobotOperatingMode.IDLE
        return True

    async def emergency_stop(self) -> bool:
        self._mode = RobotOperatingMode.ESTOP
        self._is_moving = False
        self._error_message = "EMERGENCY STOP TRIGGERED"
        return True

    async def home(self) -> bool:
        target = JointAngles(j1=0.0, j2=0.0, j3=0.0, j4=0.0, j5=0.0, j6=0.0)
        return await self.move_joints(target, speed=1.5)

    async def move_joints(self, target: JointAngles, speed: float = 1.0) -> bool:
        if self._mode == RobotOperatingMode.ESTOP:
            return False

        self._is_moving = True
        self._mode = RobotOperatingMode.MANUAL

        # Smooth simulation motion over 5 interpolation steps
        steps = 5
        delay = max(0.04, 0.2 / max(0.1, speed))

        start = self._joints.to_list()
        end = target.to_list()

        for step in range(1, steps + 1):
            if self._mode == RobotOperatingMode.ESTOP:
                return False
            interp = [
                start[i] + (end[i] - start[i]) * (step / steps)
                for i in range(6)
            ]
            self._joints = JointAngles.from_list([round(val, 2) for val in interp])
            self._pose = self._calculate_fk(self._joints)
            await asyncio.sleep(delay)

        self._joints = target
        self._pose = self._calculate_fk(self._joints)
        self._is_moving = False
        self._mode = RobotOperatingMode.IDLE
        return True

    async def move_pose(self, target: Pose3D, speed: float = 1.0) -> bool:
        """
        Inverse kinematics approximation: calculates matching joints for requested pose.
        """
        if self._mode == RobotOperatingMode.ESTOP:
            return False

        # Simplified inverse calculation to approximate target cartesian position
        r = math.sqrt(target.x**2 + target.y**2)
        base_angle = math.degrees(math.atan2(target.x, target.y)) if target.y != 0 else 0.0
        
        # Simple reach mapping
        norm_r = min(350.0, max(100.0, r))
        shoulder = (norm_r / 350.0) * 45.0
        elbow = (target.z / 350.0) * 60.0

        approx_joints = JointAngles(
            j1=round(base_angle, 1),
            j2=round(shoulder, 1),
            j3=round(elbow, 1),
            j4=round(target.pitch, 1),
            j5=round(target.roll, 1),
            j6=round(target.yaw, 1),
        )
        return await self.move_joints(approx_joints, speed)

    async def set_gripper(self, position: float) -> bool:
        pos = max(0.0, min(100.0, position))
        state = "CLOSED" if pos > 85.0 else ("OPEN" if pos < 15.0 else "GRIPPING")
        self._gripper = GripperState(position=pos, state=state)
        await asyncio.sleep(0.15)
        return True
