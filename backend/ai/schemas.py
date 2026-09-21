from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import time
import uuid


class ActionType(str, Enum):
    MOVE_JOINTS = "MOVE_JOINTS"
    MOVE_POSE = "MOVE_POSE"
    SET_GRIPPER = "SET_GRIPPER"
    HOME = "HOME"
    WAIT = "WAIT"
    DETECT_OBJECT = "DETECT_OBJECT"
    PICK_AND_PLACE = "PICK_AND_PLACE"
    PICK_AND_TRANSFER = "PICK_AND_TRANSFER"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class ObjectAttributes(BaseModel):
    """Dynamically extracted visual & physical attributes of target objects."""
    color: Optional[str] = Field(None, description="Color (e.g. red, blue, green, yellow, black)")
    size: Optional[str] = Field(None, description="Size descriptor (e.g. small, large, medium)")
    shape: Optional[str] = Field(None, description="Geometry (e.g. cylinder, cube, round, rectangular)")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary additional attributes")


class TargetObject(BaseModel):
    """Target object entity extracted from natural language command."""
    name: str = Field(..., description="Generic name or class of the object (e.g. bottle, cup, mouse, keyboard, person)")
    color: Optional[str] = Field(None, description="Direct color attribute (e.g. red, blue, green)")
    attributes: ObjectAttributes = Field(default_factory=ObjectAttributes)
    quantity: Optional[Union[int, str]] = Field(1, description="Quantity/count (e.g. 1, 2, 'all')")

    def __init__(self, **data: Any):
        super().__init__(**data)
        # Synchronize color between direct field and attributes
        if self.color and not self.attributes.color:
            self.attributes.color = self.color
        elif self.attributes.color and not self.color:
            self.color = self.attributes.color


class StructuredTask(BaseModel):
    """
    Validated internal representation of an interpreted natural-language instruction.
    Does not rely on database lookups or hardcoded predefined phrases.
    """
    raw_command: str = Field(..., description="Original user instruction")
    action: str = Field(
        ...,
        description="Standardized action (e.g. 'pick_and_transfer', 'pick', 'pick_and_place', 'find', 'move', 'home', etc.)"
    )
    object: Optional[TargetObject] = Field(None, description="Extracted target object details")
    source: Optional[str] = Field(None, description="Source robot or location (e.g. 'diy_arm', 'jetarm', 'table', 'workspace')")
    destination: Optional[str] = Field(None, description="Destination robot or location (e.g. 'jetarm', 'diy_arm', 'right', 'bin_a')")
    confidence: float = Field(0.95, ge=0.0, le=1.0)
    summary: str = Field("", description="Human-readable synthesis of the parsed intent")


class RobotAction(BaseModel):
    """An individual atomic action step in an execution plan."""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: ActionType
    robot_id: str = Field("jetarm", description="'diy_arm', 'jetarm', or 'both'")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: str
    estimated_duration_sec: float = 1.0


class ActionPlan(BaseModel):
    """Decomposed executable plan produced from the StructuredTask."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    raw_command: str
    intent: str
    target_robot: str
    structured_task: Optional[StructuredTask] = None
    actions: List[RobotAction]
    confidence: float = Field(0.95, ge=0.0, le=1.0)
    explanation: str
    created_at: float = Field(default_factory=time.time)


class NaturalLanguageCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Arbitrary natural-language instruction")
    preferred_robot: Optional[str] = Field(None, description="Optional target robot hint: 'diy_arm' or 'jetarm'")


# Schemas for Natural Language Command -> Object Matching
class PixelBoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class PixelPoint2D(BaseModel):
    x: int
    y: int


class MatchedTarget(BaseModel):
    """
    Validated target object located by YOLO and OpenCV color estimator.
    Coordinates are STRICTLY in camera image pixel space.
    """
    name: str = Field(..., description="Detected object class (e.g. 'bottle', 'cup', 'mouse')")
    color: Optional[str] = Field(None, description="Estimated dominant color (e.g. 'red', 'blue', 'green')")
    confidence: float = Field(..., description="Detection confidence score")
    bounding_box: PixelBoundingBox
    center: PixelPoint2D
    coordinate_frame: str = Field("IMAGE_COORDINATES_PIXELS", description="Sensor pixel coordinates")
    robot_coordinates: Optional[Dict[str, Any]] = Field(None, description="Robot coordinates are pending physical calibration")


class CommandMatchRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Natural language command (e.g. 'Pick the red bottle.')")
    preferred_robot: Optional[str] = Field(None, description="Optional robot preference")
    use_live_camera: bool = Field(True, description="Whether to analyze live camera stream")


class CommandMatchResponse(BaseModel):
    status: str = Field(..., description="'MATCH_FOUND', 'NOT_FOUND', or 'AMBIGUOUS'")
    understanding: str = Field(..., description="Acknowledgment: 'I understood that you want me to pick the red bottle.'")
    task: StructuredTask = Field(..., description="Extracted structured task representation")
    found: bool = Field(..., description="Whether a matching object was detected")
    target: Optional[MatchedTarget] = Field(None, description="Selected validated target object")
    candidates: List[MatchedTarget] = Field(default_factory=list, description="All candidate objects matching query")
    ambiguous: bool = Field(False, description="True if multiple matching candidates exist")
    reason: str = Field(..., description="Human-readable outcome description")
    camera_active: bool = Field(False, description="Whether live camera feed was used")
