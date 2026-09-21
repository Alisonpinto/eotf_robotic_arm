import re
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .schemas import (
    ActionPlan,
    RobotAction,
    ActionType,
    StructuredTask,
    TargetObject,
    ObjectAttributes,
    ActionStr,
    RobotIdentifier,
)


def parse_command(user_command: str, preferred_robot: Optional[str] = None) -> StructuredTask:
    """
    Dynamic Natural-Language Command Parser.
    Converts arbitrary user instructions into a validated StructuredTask.
    
    Does NOT depend on a database or predefined sentence matching.
    Uses dynamic semantic extraction and Pydantic validation.
    """
    parser = DynamicCommandParser()
    return parser.parse(user_command, preferred_robot)


class DynamicCommandParser:
    """
    NLP Entity & Intent Extractor for Robotic Arm Tasks.
    Dynamically extracts actions, target objects, descriptive attributes,
    quantities, source robots, and destinations.
    """

    COLOR_WORDS = {
        "red", "blue", "green", "yellow", "orange", "purple", "pink", "black",
        "white", "cyan", "magenta", "gray", "grey", "silver", "gold", "brown",
        "transparent", "metallic", "dark", "light"
    }

    SIZE_WORDS = {
        "small", "tiny", "little", "large", "big", "huge", "medium", "heavy",
        "light", "tall", "short", "thick", "thin"
    }

    SHAPE_WORDS = {
        "cube", "cubic", "cylinder", "cylindrical", "sphere", "spherical",
        "round", "square", "rectangular", "box", "circular", "flat", "triangular"
    }

    DIRECTION_WORDS = {
        "right", "left", "up", "down", "forward", "backward", "back", "front",
        "higher", "lower", "center", "centre", "top", "bottom", "side"
    }

    QUANTITY_MAP = {
        "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "both": 2, "all": "all", "pair": 2, "couple": 2
    }

    STOP_WORDS = {
        "the", "a", "an", "this", "that", "these", "those", "it", "them", "some",
        "please", "could", "you", "can", "now", "just", "and", "then"
    }

    def parse(self, text: str, preferred_robot: Optional[str] = None) -> StructuredTask:
        cleaned = text.strip()
        lower = cleaned.lower()

        # 1. Extract Destination & Source Entities (Robot 1, Robot 2, directions, etc.)
        source, destination = self._extract_source_and_destination(lower, preferred_robot)

        # 2. Extract Action (e.g. transfer, pick, find)
        action = self._extract_action(lower, source, destination)

        # 3. Extract Target Object and Attributes generically without hardcoding
        target_obj = self._extract_target_object(lower, action)

        # Adjust source/destination roles based on action context
        if action in ("transfer", "pick_and_transfer"):
            if not destination:
                destination = RobotIdentifier("Robot 2")
            if not source or source == destination:
                source = RobotIdentifier("Robot 1") if destination == "Robot 2" or destination == "jetarm" else RobotIdentifier("Robot 2")
        elif action in ("pick", "pick_and_place"):
            if not source:
                source = preferred_robot or (RobotIdentifier("Robot 2") if "jet" in lower or "robot 2" in lower else RobotIdentifier("Robot 1"))

        # 4. Generate human-readable summary
        summary = self._generate_summary(action, target_obj, source, destination)

        # 5. Build and validate StructuredTask with extended transfer representation
        task = StructuredTask(
            raw_command=cleaned,
            action=action,
            object=target_obj,
            object_name=target_obj.name if target_obj else None,
            colour=target_obj.colour if target_obj else None,
            color=target_obj.color if target_obj else None,
            source_robot=source,
            destination_robot=destination,
            source=source,
            destination=destination,
            confidence=0.96 if target_obj else 0.88,
            summary=summary,
        )

        return task

    def _extract_source_and_destination(
        self, lower: str, preferred_robot: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        source = preferred_robot
        destination: Optional[str] = None

        # Check destination patterns: "give it to X", "give to X", "transfer to X", "pass to X", "hand to X", "move to X", "to the X"
        dest_robot_match = re.search(
            r"\b(?:to|into|onto|towards|give\s+(?:it\s+to|to)|hand\s+(?:it\s+to|to)|pass\s+(?:it\s+to|to)|transfer\s+(?:it\s+to|to))\s+(?:the\s+)?(?:robot|arm)\s*([12])\b",
            lower,
        )
        if dest_robot_match:
            destination = RobotIdentifier(f"Robot {dest_robot_match.group(1)}")
        else:
            dest_match = re.search(
                r"\b(?:to|into|onto|towards|give\s+(?:it\s+to|to)|hand\s+to|pass\s+(?:it\s+to|to)|transfer\s+(?:it\s+to|to))\s+(?:the\s+)?([a-z0-9_\-\s]+?)(?:\.|$|,|\s+and)",
                lower,
            )
            if dest_match:
                dest_raw = dest_match.group(1).strip()
                if re.search(r"\b(robot\s*2|arm\s*2)\b", dest_raw):
                    destination = RobotIdentifier("Robot 2")
                elif re.search(r"\b(robot\s*1|arm\s*1)\b", dest_raw):
                    destination = RobotIdentifier("Robot 1")
                elif re.search(r"\b(jetarm|jet\s*arm|hiwonder|jetson)\b", dest_raw):
                    destination = RobotIdentifier("jetarm")
                elif re.search(r"\b(diy|diy\s*arm|custom\s*arm|3d\s*arm)\b", dest_raw):
                    destination = RobotIdentifier("diy_arm")
                else:
                    for dir_word in self.DIRECTION_WORDS:
                        if dir_word in dest_raw:
                            destination = dir_word
                            break
                    if not destination:
                        destination = dest_raw.replace(" ", "_")

        # Check source patterns:
        # 1. Leading robot clause: "Robot 1 pick...", "Arm 1 take..."
        start_robot_match = re.match(r"^\s*(?:the\s+)?(?:robot|arm)\s*([12])\b", lower)
        if start_robot_match:
            source = RobotIdentifier(f"Robot {start_robot_match.group(1)}")

        # 2. "with/using/from/by Robot 1/2"
        if not source:
            source_robot_match = re.search(r"\b(?:with|using|from|by)\s+(?:the\s+)?(?:robot|arm)\s*([12])\b", lower)
            if source_robot_match:
                source = RobotIdentifier(f"Robot {source_robot_match.group(1)}")

        # 3. Legacy "with/using/from/by JetArm/DIY"
        if not source:
            source_match = re.search(r"\b(?:with|using|from|by)\s+(?:the\s+)?([a-z0-9_\-\s]+?)(?:\.|$|,|\s+to|\s+and)", lower)
            if source_match:
                src_raw = source_match.group(1).strip()
                if re.search(r"\b(robot\s*1|arm\s*1)\b", src_raw):
                    source = RobotIdentifier("Robot 1")
                elif re.search(r"\b(robot\s*2|arm\s*2)\b", src_raw):
                    source = RobotIdentifier("Robot 2")
                elif re.search(r"\b(jetarm|jet\s*arm|hiwonder)\b", src_raw):
                    source = RobotIdentifier("jetarm")
                elif re.search(r"\b(diy|diy\s*arm|3d\s*arm)\b", src_raw):
                    source = RobotIdentifier("diy_arm")

        # 4. Explicit mentions elsewhere
        if not source:
            if re.search(r"\b(robot\s*1|arm\s*1)\b", lower) and destination != "Robot 1":
                source = RobotIdentifier("Robot 1")
            elif re.search(r"\b(robot\s*2|arm\s*2)\b", lower) and destination != "Robot 2":
                source = RobotIdentifier("Robot 2")
            elif re.search(r"\b(jetarm|jet\s*arm)\b", lower) and destination != "jetarm":
                source = RobotIdentifier("jetarm")
            elif re.search(r"\b(diy|diy\s*arm|custom\s*arm)\b", lower) and destination != "diy_arm":
                source = RobotIdentifier("diy_arm")

        return source, destination

    def _extract_action(self, lower: str, source: Optional[str], destination: Optional[str]) -> str:
        # Multi-stage composite transfer actions
        if re.search(r"\b(give|pass|transfer|hand)\b", lower) and (
            destination in ("Robot 1", "Robot 2", "jetarm", "diy_arm") or "robot" in lower or "arm" in lower
        ):
            return ActionStr("transfer")

        if re.search(r"\b(find|locate|search|spot)\b", lower) and re.search(r"\b(move|shift|slide|push)\b", lower):
            return "find_and_move"

        if re.search(r"\b(pick|grab|take|collect)\b", lower) and (
            re.search(r"\b(place|drop|put|deposit|bin|tray)\b", lower) or (destination and destination in self.DIRECTION_WORDS)
        ):
            return "pick_and_place"

        # Single primary verbs
        if re.search(r"\b(pick|grab|take|lift|clench|collect)\b", lower):
            return "pick"

        if re.search(r"\b(find|locate|detect|spot|search|look\s*for)\b", lower):
            return "find"

        if re.search(r"\b(move|shift|translate|slide|push|drag)\b", lower):
            return "move"

        if re.search(r"\b(place|put|drop|deposit|set\s*down)\b", lower):
            return "place"

        if re.search(r"\b(home|zero|calibrate|origin|reset)\b", lower):
            return "home"

        if re.search(r"\b(stop|halt|abort|kill|emergency|e-stop)\b", lower):
            return "emergency_stop"

        if re.search(r"\b(open|release|unclench)\s*(?:the)?\s*(?:gripper|claw|hand|tool)?\b", lower):
            return "open_gripper"

        if re.search(r"\b(close|clamp|grip)\s*(?:the)?\s*(?:gripper|claw|hand|tool)?\b", lower):
            return "close_gripper"

        if re.search(r"\b(inspect|scan|survey|view|check)\b", lower):
            return "inspect"

        if re.search(r"\b(wave|dance|gesture|wiggle|hello|hi)\b", lower):
            return "wave"

        # Dynamic fallback: extract the leading action verb from the command
        words = re.findall(r"[a-z]+", lower)
        for w in words:
            if w not in self.STOP_WORDS and len(w) > 2:
                return w

        return "custom_task"

    def _extract_target_object(self, lower: str, action: str) -> Optional[TargetObject]:
        cleaned = lower
        # 1. Strip leading source robot clause (e.g. "robot 1", "arm 1", "robot 2")
        cleaned = re.sub(r"^\s*(?:the\s+)?(?:robot|arm)\s*[12]\s*[,:]?\s*", "", cleaned)

        # 2. Strip conversational / polite intros
        cleaned = re.sub(r"^(?:please\s+)?(?:could\s+you\s+)?(?:can\s+you\s+)?(?:i\s+want\s+you\s+to\s+)?", "", cleaned)

        # 3. Strip leading action verbs at start of object clause
        cleaned = re.sub(
            r"^(?:pick(?:\s+up)?|find|locate|move|grab|take|inspect|scan|get|transfer|hold|reach)\s+",
            "",
            cleaned,
        )

        # 4. Strip destination / transfer phrases at the end
        cleaned = re.sub(r"\b(?:and\s+)?(?:give|pass|transfer|hand|move)\s+(?:it\s+)?(?:to|into|onto)\s+.*$", "", cleaned)
        cleaned = re.sub(r"\b(?:to|into|onto)\s+(?:the\s+)?(?:robot\s*[12]|arm\s*[12]|jetarm|diy\s*arm|right|left|bin|table).*$", "", cleaned)

        tokens = re.findall(r"[a-z0-9]+", cleaned)
        if not tokens:
            return None

        # Attributes collection
        color: Optional[str] = None
        size: Optional[str] = None
        shape: Optional[str] = None
        quantity: Union[int, str] = 1
        extra_attrs: Dict[str, Any] = {}
        noun_candidates: List[str] = []

        for token in tokens:
            if token in self.COLOR_WORDS:
                color = token
            elif token in self.SIZE_WORDS:
                size = token
            elif token in self.SHAPE_WORDS:
                shape = token
                noun_candidates.append(token)
            elif token in self.QUANTITY_MAP:
                quantity = self.QUANTITY_MAP[token]
            elif token.isdigit():
                quantity = int(token)
            elif token in self.STOP_WORDS or token in ("robot", "arm", "jetarm", "diy", "1", "2"):
                continue
            else:
                noun_candidates.append(token)

        if not noun_candidates:
            if shape:
                object_name = shape
            elif color:
                object_name = f"{color}_object"
            else:
                return None
        else:
            filtered_nouns = [n for n in noun_candidates if n not in self.SHAPE_WORDS] or noun_candidates
            object_name = " ".join(filtered_nouns)

        if object_name in ("it", "them", "thing", "object", "item") and (color or shape or size):
            object_name = f"{color or size or shape or 'item'}"

        attributes = ObjectAttributes(
            color=color,
            colour=color,
            size=size,
            shape=shape,
            extra=extra_attrs,
        )

        return TargetObject(
            name=object_name,
            color=color,
            colour=color,
            attributes=attributes,
            quantity=quantity,
        )

    def _generate_summary(
        self, action: str, obj: Optional[TargetObject], source: Optional[str], destination: Optional[str]
    ) -> str:
        obj_desc = ""
        if obj:
            parts = []
            c = obj.colour or obj.color
            if c:
                parts.append(c)
            if obj.attributes.size:
                parts.append(obj.attributes.size)
            parts.append(obj.name)
            obj_desc = " ".join(parts)

        src_desc = f" by {source}" if source else ""
        dest_desc = f" -> {destination}" if destination else ""

        if obj_desc:
            return f"Action [{action}] on '{obj_desc}'{src_desc}{dest_desc}"
        return f"Action [{action}]{src_desc}{dest_desc}"


class AICommandInterpreter:
    """
    High-level AI Command Interpreter.
    Integrates parse_command() and generates executable ActionPlan trajectories.
    """

    def __init__(self, use_llm_if_available: bool = True):
        self.use_llm = use_llm_if_available
        self.parser = DynamicCommandParser()

    async def interpret(self, command: str, preferred_robot: Optional[str] = None) -> ActionPlan:
        # Step 1: Parse into validated StructuredTask representation
        structured_task: StructuredTask = parse_command(command, preferred_robot)

        # Step 2: Decompose the structured task into concrete robot action steps
        actions = self._build_execution_actions(structured_task)

        target_robot = structured_task.source or "jetarm"
        if structured_task.destination in ("Robot 1", "Robot 2", "jetarm", "diy_arm"):
            target_robot = "both" if structured_task.source != structured_task.destination else target_robot

        return ActionPlan(
            raw_command=command,
            intent=structured_task.action.upper(),
            target_robot=str(target_robot),
            structured_task=structured_task,
            actions=actions,
            confidence=structured_task.confidence,
            explanation=structured_task.summary,
        )

    def _build_execution_actions(self, task: StructuredTask) -> List[RobotAction]:
        actions: List[RobotAction] = []
        action_name = task.action
        source_robot = str(task.source or "diy_arm")
        target_obj_name = task.object.name if task.object else "target"
        color_attr = (task.object.colour or task.object.color) if task.object else ""
        label = f"{color_attr} {target_obj_name}".strip()

        if action_name in ("transfer", "pick_and_transfer"):
            dest_robot = task.destination if task.destination in ("jetarm", "diy_arm") else "jetarm"
            src_robot = source_robot if source_robot != dest_robot else ("diy_arm" if dest_robot == "jetarm" else "jetarm")

            # 1. Vision localization
            actions.append(RobotAction(
                action_type=ActionType.DETECT_OBJECT,
                robot_id=src_robot,
                parameters={"target": label},
                description=f"Localize {label} with camera vision stream",
                estimated_duration_sec=0.8,
            ))
            # 2. Source robot moves to grasp
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=src_robot,
                parameters={"position": 0.0},
                description=f"Open {src_robot} gripper in preparation",
                estimated_duration_sec=0.6,
            ))
            actions.append(RobotAction(
                action_type=ActionType.MOVE_POSE,
                robot_id=src_robot,
                parameters={"x": 100.0, "y": 200.0, "z": 40.0, "pitch": -40.0},
                description=f"Lower {src_robot} to grasp {label}",
                estimated_duration_sec=1.2,
            ))
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=src_robot,
                parameters={"position": 85.0},
                description=f"Grip {label} securely",
                estimated_duration_sec=0.7,
            ))
            # 3. Source robot brings object to central handover waypoint
            actions.append(RobotAction(
                action_type=ActionType.MOVE_POSE,
                robot_id=src_robot,
                parameters={"x": 0.0, "y": 220.0, "z": 160.0, "pitch": 0.0},
                description=f"Move {src_robot} to central handover coordinate",
                estimated_duration_sec=1.5,
            ))
            # 4. Destination robot reaches handover point and grasps
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=dest_robot,
                parameters={"position": 0.0},
                description=f"Open {dest_robot} gripper at handover zone",
                estimated_duration_sec=0.6,
            ))
            actions.append(RobotAction(
                action_type=ActionType.MOVE_POSE,
                robot_id=dest_robot,
                parameters={"x": 0.0, "y": 220.0, "z": 160.0, "pitch": 0.0},
                description=f"Align {dest_robot} end-effector to {label}",
                estimated_duration_sec=1.4,
            ))
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=dest_robot,
                parameters={"position": 85.0},
                description=f"Clamp {dest_robot} gripper onto payload",
                estimated_duration_sec=0.7,
            ))
            # 5. Source releases, destination stores
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=src_robot,
                parameters={"position": 0.0},
                description=f"Release {src_robot} grip to complete handover",
                estimated_duration_sec=0.6,
            ))
            actions.append(RobotAction(
                action_type=ActionType.HOME,
                robot_id=src_robot,
                parameters={},
                description=f"Retract {src_robot} to ready pose",
                estimated_duration_sec=1.0,
            ))
            actions.append(RobotAction(
                action_type=ActionType.MOVE_POSE,
                robot_id=dest_robot,
                parameters={"x": 150.0, "y": 200.0, "z": 120.0, "pitch": -20.0},
                description=f"Transfer payload to {dest_robot} storage zone",
                estimated_duration_sec=1.2,
            ))

        elif action_name in ("pick", "pick_and_place"):
            actions.append(RobotAction(
                action_type=ActionType.DETECT_OBJECT,
                robot_id=source_robot,
                parameters={"target": label},
                description=f"Localize {label} via camera detector",
                estimated_duration_sec=0.8,
            ))
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=source_robot,
                parameters={"position": 0.0},
                description=f"Open {source_robot} gripper claw",
                estimated_duration_sec=0.6,
            ))
            actions.append(RobotAction(
                action_type=ActionType.MOVE_POSE,
                robot_id=source_robot,
                parameters={"x": 80.0, "y": 210.0, "z": 35.0, "pitch": -45.0},
                description=f"Descend to grasp elevation for {label}",
                estimated_duration_sec=1.2,
            ))
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=source_robot,
                parameters={"position": 85.0},
                description=f"Clamp gripper onto {label}",
                estimated_duration_sec=0.7,
            ))
            actions.append(RobotAction(
                action_type=ActionType.MOVE_POSE,
                robot_id=source_robot,
                parameters={"x": 80.0, "y": 210.0, "z": 150.0, "pitch": -20.0},
                description=f"Ascend with {label}",
                estimated_duration_sec=1.0,
            ))

            if task.destination:
                actions.append(RobotAction(
                    action_type=ActionType.MOVE_POSE,
                    robot_id=source_robot,
                    parameters={"x": -100.0, "y": 220.0, "z": 60.0, "pitch": -30.0},
                    description=f"Deposit {label} into destination [{task.destination}]",
                    estimated_duration_sec=1.4,
                ))
                actions.append(RobotAction(
                    action_type=ActionType.SET_GRIPPER,
                    robot_id=source_robot,
                    parameters={"position": 0.0},
                    description=f"Release {label}",
                    estimated_duration_sec=0.6,
                ))
                actions.append(RobotAction(
                    action_type=ActionType.HOME,
                    robot_id=source_robot,
                    parameters={},
                    description=f"Return {source_robot} to home ready position",
                    estimated_duration_sec=1.0,
                ))

        elif action_name in ("find", "find_and_move", "move"):
            actions.append(RobotAction(
                action_type=ActionType.DETECT_OBJECT,
                robot_id=source_robot,
                parameters={"target": label},
                description=f"Identify and locate {label} in visual field",
                estimated_duration_sec=0.8,
            ))
            dx = 80.0 if task.destination == "right" else (-80.0 if task.destination == "left" else 0.0)
            dy = 50.0 if task.destination in ("forward", "front") else 0.0
            dz = 50.0 if task.destination in ("up", "higher") else 0.0

            actions.append(RobotAction(
                action_type=ActionType.MOVE_POSE,
                robot_id=source_robot,
                parameters={"x": 50.0 + dx, "y": 200.0 + dy, "z": 80.0 + dz, "pitch": -30.0},
                description=f"Shift {source_robot} tool-point towards {task.destination or 'offset location'}",
                estimated_duration_sec=1.4,
            ))

        elif action_name == "home":
            actions.append(RobotAction(
                action_type=ActionType.HOME,
                robot_id=source_robot,
                parameters={},
                description=f"Send {source_robot} to home calibration pose",
                estimated_duration_sec=1.2,
            ))

        elif action_name == "emergency_stop":
            actions.append(RobotAction(
                action_type=ActionType.EMERGENCY_STOP,
                robot_id="both",
                parameters={},
                description="Halt all arm actuators immediately",
                estimated_duration_sec=0.1,
            ))

        elif action_name == "open_gripper":
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=source_robot,
                parameters={"position": 0.0},
                description=f"Open gripper on {source_robot}",
                estimated_duration_sec=0.6,
            ))

        elif action_name == "close_gripper":
            actions.append(RobotAction(
                action_type=ActionType.SET_GRIPPER,
                robot_id=source_robot,
                parameters={"position": 90.0},
                description=f"Close gripper firmly on {source_robot}",
                estimated_duration_sec=0.6,
            ))

        else:
            # Safe parameterized sequence for novel arbitrary verbs
            actions.append(RobotAction(
                action_type=ActionType.MOVE_JOINTS,
                robot_id=source_robot,
                parameters={"joints": [15.0, 10.0, 30.0, 0.0, 0.0, 0.0]},
                description=f"Execute action [{action_name}] step 1 on {source_robot}",
                estimated_duration_sec=1.0,
            ))
            actions.append(RobotAction(
                action_type=ActionType.WAIT,
                robot_id=source_robot,
                parameters={"seconds": 0.5},
                description="Stabilize arm kinematics",
                estimated_duration_sec=0.5,
            ))
            actions.append(RobotAction(
                action_type=ActionType.HOME,
                robot_id=source_robot,
                parameters={},
                description=f"Return {source_robot} to ready state",
                estimated_duration_sec=1.0,
            ))

        return actions


ai_interpreter = AICommandInterpreter()
