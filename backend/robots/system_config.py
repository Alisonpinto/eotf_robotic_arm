from typing import List, Union, Any, Dict
try:
    from pydantic import BaseModel, Field, field_validator, model_validator
except ImportError:
    try:
        from ai.schemas import BaseModel, Field, field_validator, model_validator
    except ImportError:
        from ..ai.schemas import BaseModel, Field, field_validator, model_validator


PLACEHOLDER_MEASUREMENT = "PLACEHOLDER — REPLACE WITH REAL MEASUREMENT"


class JointConfig(BaseModel):
    """Configuration for a single robot joint."""
    name: str = Field(..., description="Name of the joint")
    limit_min: float = Field(0.0, description="Placeholder minimum joint limit in degrees")
    limit_max: float = Field(180.0, description="Placeholder maximum joint limit in degrees")


class RobotBaseConfig(BaseModel):
    """
    Fixed base physical position configuration for a robot.
    Immutable to ensure the robot base location is never changed programmatically.
    """
    x: Union[float, str] = Field(PLACEHOLDER_MEASUREMENT, description="Fixed base X position")
    y: Union[float, str] = Field(PLACEHOLDER_MEASUREMENT, description="Fixed base Y position")
    z: Union[float, str] = Field(PLACEHOLDER_MEASUREMENT, description="Fixed base Z position")
    is_fixed_base: bool = Field(True, description="Strict enforcement that the base cannot move")

    # Make the base configuration immutable so it cannot be altered during execution
    class Config:
        frozen = True

    @field_validator('is_fixed_base')
    @classmethod
    def must_be_fixed(cls, v):
        if not v:
            raise ValueError("Robot base MUST be fixed for this system design.")
        return v


class RobotConfig(BaseModel):
    """
    Configuration representing a fixed-base 6-DOF robotic arm.
    """
    robot_id: str = Field(..., description="Unique ID for the robot")
    name: str = Field(..., description="Human-readable name")
    is_enabled: bool = Field(True, description="Enabled status of the robot")
    base_position: RobotBaseConfig = Field(
        default_factory=RobotBaseConfig,
        description="Immutable fixed base coordinates"
    )
    joints: List[JointConfig] = Field(..., description="Exactly 6 joints required")
    has_gripper: bool = Field(True, description="Indicates if the robot is equipped with a gripper")

    @field_validator('joints')
    @classmethod
    def validate_6_dof(cls, v):
        if len(v) != 6:
            raise ValueError(f"Robot MUST have exactly 6 joints. Found {len(v)}.")
        return v


class HandoffPointConfig(BaseModel):
    """
    Fixed spatial point where Robot 1 hands objects to Robot 2.
    """
    x: Union[float, str] = Field(PLACEHOLDER_MEASUREMENT, description="Handoff point X")
    y: Union[float, str] = Field(PLACEHOLDER_MEASUREMENT, description="Handoff point Y")
    z: Union[float, str] = Field(PLACEHOLDER_MEASUREMENT, description="Handoff point Z")


class RoboticsSystemConfig(BaseModel):
    """
    Root configuration for the dual-arm robotics system.
    """
    robot_1: RobotConfig
    robot_2: RobotConfig
    handoff_point: HandoffPointConfig

    @model_validator(mode='after')
    def check_placeholders(self) -> 'RoboticsSystemConfig':
        """
        Validate and flag if any placeholders are still in use, ensuring
        developers are aware physical measurements are pending.
        """
        placeholders_found = False
        
        # Check handoff
        if self.handoff_point.x == PLACEHOLDER_MEASUREMENT or self.handoff_point.y == PLACEHOLDER_MEASUREMENT or self.handoff_point.z == PLACEHOLDER_MEASUREMENT:
            placeholders_found = True
            
        # Check bases
        for r in [self.robot_1, self.robot_2]:
            if r.base_position.x == PLACEHOLDER_MEASUREMENT or r.base_position.y == PLACEHOLDER_MEASUREMENT or r.base_position.z == PLACEHOLDER_MEASUREMENT:
                placeholders_found = True

        if placeholders_found:
            print("[WARNING] The Robotics System is currently using PLACEHOLDER measurements for physical coordinates.")
            print("[WARNING] DO NOT execute physical movement commands until REAL measurements are entered.")
            
        return self


# Default Initial Configuration Factory
def create_default_system_config() -> RoboticsSystemConfig:
    """
    Generates the default generic placeholder configuration for Step 3.
    """
    joints_1 = [
        JointConfig(name="Base_Rotation", limit_min=-180, limit_max=180),
        JointConfig(name="Shoulder_Pitch", limit_min=-90, limit_max=90),
        JointConfig(name="Elbow_Pitch", limit_min=-135, limit_max=135),
        JointConfig(name="Wrist_Pitch", limit_min=-90, limit_max=90),
        JointConfig(name="Wrist_Roll", limit_min=-180, limit_max=180),
        JointConfig(name="Wrist_Yaw", limit_min=-180, limit_max=180),
    ]
    
    joints_2 = [
        JointConfig(name="Base_Rotation", limit_min=-180, limit_max=180),
        JointConfig(name="Shoulder_Pitch", limit_min=-90, limit_max=90),
        JointConfig(name="Elbow_Pitch", limit_min=-135, limit_max=135),
        JointConfig(name="Wrist_Pitch", limit_min=-90, limit_max=90),
        JointConfig(name="Wrist_Roll", limit_min=-180, limit_max=180),
        JointConfig(name="Wrist_Yaw", limit_min=-180, limit_max=180),
    ]

    return RoboticsSystemConfig(
        robot_1=RobotConfig(
            robot_id="R1",
            name="Robot 1 (DIY Arm)",
            joints=joints_1,
            base_position=RobotBaseConfig()
        ),
        robot_2=RobotConfig(
            robot_id="R2",
            name="Robot 2 (JetArm)",
            joints=joints_2,
            base_position=RobotBaseConfig()
        ),
        handoff_point=HandoffPointConfig()
    )


# Singleton Instance
system_config = create_default_system_config()
