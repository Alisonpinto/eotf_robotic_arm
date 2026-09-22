from typing import Optional, Dict
try:
    from pydantic import BaseModel, Field, field_validator, model_validator
except ImportError:
    try:
        from ai.schemas import BaseModel, Field, field_validator, model_validator
    except ImportError:
        from ..ai.schemas import BaseModel, Field, field_validator, model_validator

# We use the existing Step 3 config for validation
from robots.system_config import system_config, RobotBaseConfig

class TargetCoordinate(BaseModel):
    """Strictly validates target spatial coordinates in millimeters."""
    x: float = Field(..., description="Target X coordinate in mm")
    y: float = Field(..., description="Target Y coordinate in mm")
    z: float = Field(..., description="Target Z coordinate in mm")

class MovementPlan(BaseModel):
    """
    Virtual representation of a planned robot movement.
    Serves as the software interface before real IK is implemented.
    """
    robot_id: str = Field(..., description="The ID of the robot executing the plan")
    target: TargetCoordinate = Field(..., description="The verified 3D target coordinate")
    base_fixed: bool = Field(True, description="Enforced strict flag that the base MUST remain fixed")
    
    # 6 Joint Placeholders
    joint_1: str = Field("PENDING_REAL_IK", description="Placeholder for Joint 1 angle")
    joint_2: str = Field("PENDING_REAL_IK", description="Placeholder for Joint 2 angle")
    joint_3: str = Field("PENDING_REAL_IK", description="Placeholder for Joint 3 angle")
    joint_4: str = Field("PENDING_REAL_IK", description="Placeholder for Joint 4 angle")
    joint_5: str = Field("PENDING_REAL_IK", description="Placeholder for Joint 5 angle")
    joint_6: str = Field("PENDING_REAL_IK", description="Placeholder for Joint 6 angle")
    
    gripper_state: str = Field("PENDING_REAL_GRIPPER", description="Target state of the gripper")
    status: str = Field("PLAN_GENERATED_PENDING_IK", description="Current status of the movement plan")

    class Config:
        # We freeze the base_fixed field so it cannot be mutated after creation
        frozen = False

    @field_validator('base_fixed')
    @classmethod
    def validate_base_remains_fixed(cls, v):
        if not v:
            raise ValueError("CRITICAL: The movement planner explicitly prevents changing the robot's base position. base_fixed must be True.")
        return v

    def enforce_immutability(self):
        """Helper to ensure we do not try to move the base."""
        if not self.base_fixed:
            raise ValueError("Base movement rejected.")

class RobotMovementPlanner:
    """
    Generates movement plans for robots while strictly enforcing physical constraints
    (such as fixed bases) and abstracting IK until real dimensions are measured.
    """
    def __init__(self):
        # Bind to the Step 3 global system config
        self.config = system_config

    def generate_plan_for_robot(
        self, 
        robot_id: str, 
        target_x: float, 
        target_y: float, 
        target_z: float,
        gripper_state: str = "PENDING_REAL_GRIPPER"
    ) -> MovementPlan:
        """
        Validates target coordinates and generates a secure virtual movement plan.
        """
        # 1. Validate Robot ID
        if robot_id not in [self.config.robot_1.robot_id, self.config.robot_2.robot_id]:
            raise ValueError(f"Invalid robot ID: '{robot_id}'. Known robots: {self.config.robot_1.robot_id}, {self.config.robot_2.robot_id}")

        # 2. Validate coordinates (Pydantic handles float casting and missing values via TargetCoordinate)
        try:
            target = TargetCoordinate(x=target_x, y=target_y, z=target_z)
        except Exception as e:
            raise ValueError(f"Invalid target coordinates provided: {e}")

        # 3. Create Virtual Plan
        plan = MovementPlan(
            robot_id=robot_id,
            target=target,
            base_fixed=True,
            gripper_state=gripper_state
        )

        return plan

# Singleton Planner Instance
movement_planner = RobotMovementPlanner()
