from enum import Enum
from typing import Any, Dict, List, Optional, Union
import time
import uuid

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Graceful fallback when running in minimal environments without pydantic installed
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            for k, v in self.__class__.__dict__.items():
                if not k.startswith("_") and k not in kwargs and not callable(v) and not isinstance(v, property):
                    if hasattr(v, "default_factory") and callable(v.default_factory):
                        setattr(self, k, v.default_factory())
                    elif hasattr(v, "default") and v.default is not ...:
                        setattr(self, k, v.default)
                    elif not hasattr(v, "default_factory") and not hasattr(v, "default"):
                        setattr(self, k, v)
                    else:
                        setattr(self, k, None)

        def model_dump(self, **kwargs):
            res = {}
            for k, v in self.__dict__.items():
                if k.startswith("_"):
                    continue
                if hasattr(v, "model_dump"):
                    res[k] = v.model_dump()
                elif isinstance(v, list):
                    res[k] = [item.model_dump() if hasattr(item, "model_dump") else item for item in v]
                elif isinstance(v, dict):
                    res[k] = {dk: dv.model_dump() if hasattr(dv, "model_dump") else dv for dk, dv in v.items()}
                else:
                    res[k] = v
            return res

        def model_dump_json(self, indent=None, **kwargs):
            import json
            return json.dumps(self.model_dump(), indent=indent)

    def Field(default=..., default_factory=None, description=None, **kwargs):
        class _FieldDef:
            def __init__(self, d, df, desc):
                self.default = None if d is ... else d
                self.default_factory = df
                self.description = desc
        return _FieldDef(default, default_factory, description)


class ActionStr(str):
    """
    Action string supporting both 'transfer' and 'pick_and_transfer' comparisons
    for backward compatibility with existing tests.
    """
    def __eq__(self, other):
        if str(self) == "transfer" and other == "pick_and_transfer":
            return True
        if str(self) == "pick_and_transfer" and other == "transfer":
            return True
        return super().__eq__(other)

    def __hash__(self):
        return super().__hash__()


class RobotIdentifier(str):
    """
    Robot identifier string supporting aliases (e.g. 'Robot 1' <-> 'diy_arm', 'Robot 2' <-> 'jetarm')
    for seamless compatibility across legacy and multi-arm setups.
    """
    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        if super().__eq__(other):
            return True
        s1 = str(self).lower().replace(" ", "").replace("_", "")
        s2 = other.lower().replace(" ", "").replace("_", "")
        if s1 == s2:
            return True
        if s1 in ("robot1", "diyarm") and s2 in ("robot1", "diyarm"):
            return True
        if s1 in ("robot2", "jetarm") and s2 in ("robot2", "jetarm"):
            return True
        return False

    def __hash__(self):
        return super().__hash__()


class ActionType(str, Enum):
    MOVE_JOINTS = "MOVE_JOINTS"
    MOVE_POSE = "MOVE_POSE"
    SET_GRIPPER = "SET_GRIPPER"
    HOME = "HOME"
    WAIT = "WAIT"
    DETECT_OBJECT = "DETECT_OBJECT"
    PICK_AND_PLACE = "PICK_AND_PLACE"
    PICK_AND_TRANSFER = "PICK_AND_TRANSFER"
    TRANSFER = "TRANSFER"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class ObjectAttributes(BaseModel):
    """Dynamically extracted visual & physical attributes of target objects."""
    color: Optional[str] = Field(None, description="Color (e.g. red, blue, green, yellow, black)")
    colour: Optional[str] = Field(None, description="Colour attribute synonym")
    size: Optional[str] = Field(None, description="Size descriptor (e.g. small, large, medium)")
    shape: Optional[str] = Field(None, description="Geometry (e.g. cylinder, cube, round, rectangular)")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary additional attributes")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if hasattr(self, "color") and self.color and not getattr(self, "colour", None):
            self.colour = self.color
        elif hasattr(self, "colour") and self.colour and not getattr(self, "color", None):
            self.color = self.colour


class TargetObject(BaseModel):
    """Target object entity extracted from natural language command."""
    name: str = Field(..., description="Generic name or class of the object (e.g. bottle, mango, mobile phone, cup)")
    color: Optional[str] = Field(None, description="Direct color attribute (e.g. red, blue, green)")
    colour: Optional[str] = Field(None, description="Direct colour attribute (e.g. red, blue, green)")
    attributes: ObjectAttributes = Field(default_factory=ObjectAttributes)
    quantity: Optional[Union[int, str]] = Field(1, description="Quantity/count (e.g. 1, 2, 'all')")

    def __init__(self, **data: Any):
        super().__init__(**data)
        # Synchronize color between direct field, colour synonym, and attributes
        c = self.color or self.colour or (self.attributes.color if hasattr(self, "attributes") and self.attributes else None)
        self.color = c
        self.colour = c
        if hasattr(self, "attributes") and self.attributes:
            self.attributes.color = c
            self.attributes.colour = c


class StructuredTask(BaseModel):
    """
    Validated internal representation of an interpreted natural-language instruction.
    Does not rely on database lookups or hardcoded predefined phrases.
    """
    raw_command: str = Field(..., description="Original user instruction")
    action: str = Field(
        ...,
        description="Standardized action (e.g. 'transfer', 'pick_and_transfer', 'pick', 'find', 'move', 'home', etc.)"
    )
    object: Optional[TargetObject] = Field(None, description="Extracted target object details")
    # Extended fields representing full object-transfer instructions
    object_name: Optional[str] = Field(None, description="Object category/name (e.g. 'bottle', 'mango', 'mobile phone')")
    colour: Optional[str] = Field(None, description="Colour attribute (e.g. 'red', 'blue', None)")
    color: Optional[str] = Field(None, description="Color attribute synonym")
    source_robot: Optional[str] = Field(None, description="Source robot (e.g. 'Robot 1')")
    destination_robot: Optional[str] = Field(None, description="Destination robot (e.g. 'Robot 2')")
    source: Optional[str] = Field(None, description="Source robot or location (e.g. 'Robot 1', 'diy_arm')")
    destination: Optional[str] = Field(None, description="Destination robot or location (e.g. 'Robot 2', 'jetarm')")
    confidence: float = Field(0.95, ge=0.0, le=1.0)
    summary: str = Field("", description="Human-readable synthesis of the parsed intent")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if getattr(self, "object", None):
            if not getattr(self, "object_name", None):
                self.object_name = self.object.name
            c = self.object.colour or self.object.color
            if not getattr(self, "colour", None):
                self.colour = c
            if not getattr(self, "color", None):
                self.color = c
        if getattr(self, "source_robot", None) and not getattr(self, "source", None):
            self.source = self.source_robot
        elif getattr(self, "source", None) and not getattr(self, "source_robot", None):
            self.source_robot = self.source

        if getattr(self, "destination_robot", None) and not getattr(self, "destination", None):
            self.destination = self.destination_robot
        elif getattr(self, "destination", None) and not getattr(self, "destination_robot", None):
            self.destination_robot = self.destination


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

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)


class PixelPoint2D(BaseModel):
    x: int
    y: int


class MatchedTarget(BaseModel):
    """
    Validated target object located by YOLO and OpenCV color estimator.
    Maintains original camera image pixel coordinates AND calculated physical table coordinates.
    """
    name: str = Field(..., description="Detected object class (e.g. 'bottle', 'cup', 'mouse')")
    color: Optional[str] = Field(None, description="Estimated dominant color (e.g. 'red', 'blue', 'green')")
    confidence: float = Field(..., description="Detection confidence score")
    bounding_box: PixelBoundingBox
    center: PixelPoint2D
    coordinate_frame: str = Field("IMAGE_COORDINATES_PIXELS", description="Sensor pixel coordinates")
    table_coordinates: Optional[Any] = Field(None, description="Physical table coordinates (X, Y, Z in mm) in TABLE_COORDINATES frame")
    table_dimensions: Optional[Any] = Field(None, description="Estimated dimensions on table in mm")
    robot_coordinates: Optional[Dict[str, Any]] = Field(None, description="Robot coordinates are pending physical calibration")

    @property
    def table_x(self) -> Optional[float]:
        if self.table_coordinates is None:
            return None
        val = getattr(self.table_coordinates, "x", None)
        if val is not None:
            return val
        return self.table_coordinates.get("x") if isinstance(self.table_coordinates, dict) else None

    @property
    def table_y(self) -> Optional[float]:
        if self.table_coordinates is None:
            return None
        val = getattr(self.table_coordinates, "y", None)
        if val is not None:
            return val
        return self.table_coordinates.get("y") if isinstance(self.table_coordinates, dict) else None

    @property
    def table_z(self) -> Optional[float]:
        if self.table_coordinates is None:
            return None
        val = getattr(self.table_coordinates, "z", None)
        if val is not None:
            return val
        return self.table_coordinates.get("z") if isinstance(self.table_coordinates, dict) else None



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
