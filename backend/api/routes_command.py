from fastapi import APIRouter, HTTPException
from typing import Optional

try:
    from ai.schemas import (
        NaturalLanguageCommandRequest,
        ActionPlan,
        StructuredTask,
        CommandMatchRequest,
        CommandMatchResponse,
    )
    from ai.interpreter import ai_interpreter, parse_command
    from tasks.task_manager import task_manager
    from tasks.models import TaskRecord
    from vision.processor import vision_processor
    from vision.detector import vision_detector
    from vision.object_matcher import object_matcher, MatchEvaluation
except ImportError:
    from ..ai.schemas import (
        NaturalLanguageCommandRequest,
        ActionPlan,
        StructuredTask,
        CommandMatchRequest,
        CommandMatchResponse,
    )
    from ..ai.interpreter import ai_interpreter, parse_command
    from ..tasks.task_manager import task_manager
    from ..tasks.models import TaskRecord
    from ..vision.processor import vision_processor
    from ..vision.detector import vision_detector
    from ..vision.object_matcher import object_matcher, MatchEvaluation

router = APIRouter(prefix="/api/command", tags=["ai_command"])


def generate_understanding_text(task: StructuredTask) -> str:
    """Generate conversational acknowledgment of the user's intent."""
    action = task.action.replace("_", " ")
    if task.object:
        color_str = f"{task.object.color} " if task.object.color else ""
        name_str = task.object.name
        target_str = f"{color_str}{name_str}".strip()

        if action == "pick and transfer":
            dest_name = "the JetArm" if task.destination == "jetarm" else (task.destination or "the other arm")
            return f"I understood that you want me to pick the {target_str} and give it to {dest_name}."
        elif action in ("pick", "take", "grab"):
            return f"I understood that you want me to pick the {target_str}."
        elif action in ("find", "locate", "detect", "look for"):
            return f"I understood that you want me to find the {target_str}."
        elif action in ("move", "shift"):
            dest_desc = f" to the {task.destination}" if task.destination else ""
            return f"I understood that you want me to move the {target_str}{dest_desc}."
        else:
            return f"I understood that you want me to {action} the {target_str}."
    return f"I understood your request: {task.summary or task.raw_command}."


@router.post("/match", response_model=CommandMatchResponse)
async def match_command_endpoint(req: CommandMatchRequest):
    """
    NATURAL LANGUAGE COMMAND -> OBJECT MATCHING PIPELINE
    
    1. AI Command Parser parses user instruction into a validated StructuredTask.
    2. Captures visual frame from the active camera source (or workspace).
    3. Runs YOLO object detector + OpenCV color estimator.
    4. Object Matcher compares the structured task query against visual detections.
    5. Returns the validated target object with image coordinates, confidence, and bounding box.
    6. Does NOT control physical robot actuators yet.
    """
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command string cannot be empty.")

    # 1. AI Command Parser -> Structured Task
    task: StructuredTask = parse_command(req.command, req.preferred_robot)
    understanding = generate_understanding_text(task)

    # 2. Get current visual frame from camera engine
    frame = vision_processor.get_raw_frame()

    # 3. Real-time YOLO Detection + Color Estimation
    detections = vision_detector.detect(frame)

    # 4. Object Matcher compares structured task against visual detections
    evaluation: MatchEvaluation = object_matcher.evaluate_match(detections, task)

    # 5. Visual indication on live stream
    if evaluation.found and evaluation.target:
        vision_processor.set_active_target(evaluation.target.model_dump())
        status = "AMBIGUOUS" if evaluation.ambiguous else "MATCH_FOUND"
    else:
        vision_processor.clear_active_target()
        status = "NOT_FOUND"

    return CommandMatchResponse(
        status=status,
        understanding=understanding,
        task=task,
        found=evaluation.found,
        target=evaluation.target,
        candidates=evaluation.candidates,
        ambiguous=evaluation.ambiguous,
        reason=evaluation.reason,
        camera_active=vision_processor.is_camera_running(),
    )


@router.post("", response_model=TaskRecord)
async def process_and_execute_command(req: NaturalLanguageCommandRequest):
    """
    Accept an arbitrary natural-language command, parse it into a validated StructuredTask,
    generate the action plan, create an executable task, and begin execution.
    """
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command string cannot be empty.")

    plan: ActionPlan = await ai_interpreter.interpret(
        command=req.command,
        preferred_robot=req.preferred_robot
    )

    task_record = task_manager.create_task(plan)
    task_manager.start_task(task_record.task_id)
    return task_record


@router.post("/parse", response_model=StructuredTask)
async def parse_command_endpoint(req: NaturalLanguageCommandRequest):
    """
    Directly parse a natural-language command into the structured task representation.
    """
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command string cannot be empty.")

    return parse_command(req.command, req.preferred_robot)


@router.post("/plan_only", response_model=ActionPlan)
async def preview_plan(req: NaturalLanguageCommandRequest):
    """
    Preview how the AI interprets the natural-language command into structured task
    and decomposed actions without executing it.
    """
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Command string cannot be empty.")

    plan: ActionPlan = await ai_interpreter.interpret(
        command=req.command,
        preferred_robot=req.preferred_robot
    )
    return plan
