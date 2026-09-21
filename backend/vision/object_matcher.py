from typing import Any, Dict, List, Optional, Union
try:
    from pydantic import BaseModel, Field
except ImportError:
    try:
        from ai.schemas import BaseModel, Field
    except ImportError:
        from ..ai.schemas import BaseModel, Field

try:
    from ai.schemas import (
        StructuredTask,
        TargetObject,
        MatchedTarget,
        PixelBoundingBox,
        PixelPoint2D,
    )
    from vision.detector import DetectedObject, Point2D, BoundingBox
except ImportError:
    from ..ai.schemas import (
        StructuredTask,
        TargetObject,
        MatchedTarget,
        PixelBoundingBox,
        PixelPoint2D,
    )
    from .detector import DetectedObject, Point2D, BoundingBox

try:
    from vision.calibration import table_calibrator, TableCoordinates, TableDimensions
except ImportError:
    try:
        from .calibration import table_calibrator, TableCoordinates, TableDimensions
    except ImportError:
        table_calibrator = None
        TableCoordinates = None
        TableDimensions = None


class ObjectMatchQuery(BaseModel):
    """Target object criteria used for matching."""
    name: Optional[str] = Field(None, description="Requested object class (e.g. 'bottle', 'cup', 'mouse')")
    color: Optional[str] = Field(None, description="Requested color (e.g. 'red', 'blue', 'green')")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class MatchResult(BaseModel):
    """
    Comprehensive result of matching a requested AI task object against visual detections.
    
    IMPORTANT ARCHITECTURAL DISTINCTIONS:
    - image_coordinates: Exact pixel coordinates on the 2D camera sensor (e.g. x: 385, y: 285).
    - table_coordinates: Physical coordinates (X, Y, Z in mm) on the fixed table plane.
    - robot_coordinates: Explicitly marked as PENDING_CALIBRATION. 
      Camera coordinates != Table coordinates != Robot coordinates.
    """
    matched: bool = Field(..., description="Whether a suitable object was found")
    matched_object: Optional[DetectedObject] = None
    match_score: float = Field(0.0, ge=0.0, le=1.0, description="Match confidence between 0.0 and 1.0")
    requested_object: Dict[str, Any] = Field(default_factory=dict)
    image_coordinates: Optional[Dict[str, Any]] = Field(
        None,
        description="2D pixel coordinates on the camera image plane"
    )
    table_coordinates: Optional[Dict[str, Any]] = Field(
        None,
        description="Physical table coordinates (X, Y, Z in mm) on the fixed table surface"
    )
    table_dimensions: Optional[Dict[str, Any]] = Field(
        None,
        description="Estimated physical dimensions on table (width_mm, length_mm)"
    )
    coordinate_frame: str = Field(
        "IMAGE_COORDINATES_PIXELS",
        description="Coordinate frame identifier for image coordinates"
    )
    table_coordinate_frame: str = Field(
        "TABLE_COORDINATES",
        description="Coordinate frame identifier for physical table coordinates"
    )
    robot_coordinates_status: str = Field(
        "UNAVAILABLE_PENDING_CALIBRATION",
        description="Robot coordinate status: Extrinsic matrix calibration required when physical camera is installed"
    )
    reasoning: str = Field(..., description="Explanation of why this detection was selected")



class MatchEvaluation(BaseModel):
    """
    Validated target matching evaluation result.
    """
    found: bool
    target: Optional[MatchedTarget] = None
    candidates: List[MatchedTarget] = Field(default_factory=list)
    ambiguous: bool = False
    reason: str


class ObjectMatcher:
    """
    Semantic and Visual Object Matcher.
    Correlates target entities from the AI command parser (e.g. 'red bottle', 'mouse')
    with real-time YOLO object detections and OpenCV color estimation.
    """

    # Category synonyms and shape compatibility
    SYNONYM_MAP = {
        "bottle": ["bottle", "cylinder", "container", "can", "canister"],
        "cup": ["cup", "mug", "glass", "can"],
        "box": ["box", "cube", "package", "block", "carton"],
        "can": ["can", "cylinder", "canister", "bottle"],
        "mouse": ["mouse"],
        "keyboard": ["keyboard"],
        "laptop": ["laptop", "computer"],
        "phone": ["cell phone", "phone", "mobile", "mobile phone"],
        "cell phone": ["cell phone", "phone", "mobile", "mobile phone"],
        "mobile phone": ["cell phone", "phone", "mobile", "mobile phone"],
        "mobile": ["cell phone", "phone", "mobile", "mobile phone"],
        "person": ["person", "human", "user"],
    }

    PLURAL_MAP = {
        "bottles": "bottle",
        "cups": "cup",
        "boxes": "box",
        "cans": "can",
        "mice": "mouse",
        "keyboards": "keyboard",
        "laptops": "laptop",
        "phones": "cell phone",
        "people": "person",
    }

    def evaluate_match(
        self,
        detected_objects: List[DetectedObject],
        task_or_query: Union[StructuredTask, ObjectMatchQuery, Dict[str, Any]],
    ) -> MatchEvaluation:
        """
        Compare requested structured command against YOLO detections.
        1. Find objects matching class name.
        2. Match color attribute using OpenCV color estimation.
        3. If no match -> found: False with clear reason.
        4. If multiple match -> found: True, ambiguous: True, candidates list.
        5. If single match -> found: True, target: MatchedTarget.
        """
        query = self._extract_query(task_or_query)
        target_name = (query.name or "").lower().strip()
        target_color = (query.color or "").lower().strip()

        # Handle plurals (e.g. "bottles" -> "bottle")
        target_name = self.PLURAL_MAP.get(target_name, target_name)

        if not detected_objects:
            color_desc = f"{target_color} " if target_color else ""
            return MatchEvaluation(
                found=False,
                target=None,
                candidates=[],
                ambiguous=False,
                reason=f"No {color_desc}{target_name or 'objects'} detected (visual frame is empty).",
            )

        # 1. Filter candidates by class / category
        class_candidates: List[DetectedObject] = []
        for obj in detected_objects:
            obj_name = obj.name.lower().strip()
            if not target_name or target_name in ("item", "object", "thing"):
                class_candidates.append(obj)
            elif obj_name == target_name:
                class_candidates.append(obj)
            elif self._are_synonyms(target_name, obj_name):
                class_candidates.append(obj)

        if not class_candidates:
            color_desc = f"{target_color} " if target_color else ""
            available_names = list(set(o.name for o in detected_objects))
            avail_str = f" (detected: {', '.join(available_names)})" if available_names else ""
            return MatchEvaluation(
                found=False,
                target=None,
                candidates=[],
                ambiguous=False,
                reason=f"No {color_desc}{target_name} detected{avail_str}.",
            )

        # 2. Filter / Score by color if requested
        matching_objects: List[DetectedObject] = []
        if target_color:
            for obj in class_candidates:
                obj_color = (obj.color or "").lower().strip()
                if obj_color == target_color:
                    matching_objects.append(obj)

            if not matching_objects:
                detected_colors = list(set(o.color for o in class_candidates if o.color))
                detected_colors_str = f" ({', '.join(detected_colors)} detected)" if detected_colors else ""
                return MatchEvaluation(
                    found=False,
                    target=None,
                    candidates=[],
                    ambiguous=False,
                    reason=f"No {target_color} {target_name} detected{detected_colors_str}.",
                )
        else:
            # No color constraint requested (e.g. "Pick the mouse")
            matching_objects = class_candidates

        # Convert matching objects to MatchedTarget schema
        matched_candidates = [self._convert_to_matched_target(obj) for obj in matching_objects]

        # 3. Check for ambiguity (multiple matches)
        if len(matched_candidates) > 1:
            color_desc = f"{target_color} " if target_color else ""
            return MatchEvaluation(
                found=True,
                target=matched_candidates[0], # Highest confidence candidate as default reference
                candidates=matched_candidates,
                ambiguous=True,
                reason=f"Multiple ({len(matched_candidates)}) {color_desc}{target_name}s detected. Candidates available for disambiguation.",
            )

        # 4. Single unambiguous match
        best_target = matched_candidates[0]
        color_desc = f"{best_target.color} " if best_target.color else ""
        return MatchEvaluation(
            found=True,
            target=best_target,
            candidates=[best_target],
            ambiguous=False,
            reason=f"Found {color_desc}{best_target.name} with {int(best_target.confidence * 100)}% confidence.",
        )

    def _convert_to_matched_target(self, obj: DetectedObject) -> MatchedTarget:
        """Convert a detected object to the validated target representation with table coordinates."""
        table_coords = getattr(obj, "table_coordinates", None)
        if table_coords is None and table_calibrator is not None:
            table_coords = table_calibrator.pixel_to_table(obj.center.x, obj.center.y)

        table_dims = getattr(obj, "table_dimensions", None)
        if table_dims is None and table_calibrator is not None:
            table_dims = table_calibrator.estimate_dimensions_mm(
                obj.bounding_box.width, obj.bounding_box.height
            )

        return MatchedTarget(
            name=obj.name,
            color=obj.color,
            confidence=round(obj.confidence, 2),
            bounding_box=PixelBoundingBox(
                x1=obj.bounding_box.x1,
                y1=obj.bounding_box.y1,
                x2=obj.bounding_box.x2,
                y2=obj.bounding_box.y2,
            ),
            center=PixelPoint2D(
                x=obj.center.x,
                y=obj.center.y,
            ),
            coordinate_frame="IMAGE_COORDINATES_PIXELS",
            table_coordinates=table_coords,
            table_dimensions=table_dims,
            robot_coordinates=None,
        )

    def match(
        self,
        detected_objects: List[DetectedObject],
        task_or_query: Union[StructuredTask, ObjectMatchQuery, Dict[str, Any]],
    ) -> MatchResult:
        """
        Legacy match method preserved for compatibility with test_backend.py and routes_vision.py.
        """
        query = self._extract_query(task_or_query)
        eval_res = self.evaluate_match(detected_objects, query)

        if eval_res.found and eval_res.target:
            # Find matching DetectedObject for the legacy structure
            orig_obj = next(
                (o for o in detected_objects if o.center.x == eval_res.target.center.x and o.center.y == eval_res.target.center.y),
                detected_objects[0]
            )
            image_coords = {
                "center": {"x": eval_res.target.center.x, "y": eval_res.target.center.y},
                "bounding_box": {
                    "x1": eval_res.target.bounding_box.x1,
                    "y1": eval_res.target.bounding_box.y1,
                    "x2": eval_res.target.bounding_box.x2,
                    "y2": eval_res.target.bounding_box.y2,
                },
                "width_pixels": eval_res.target.bounding_box.x2 - eval_res.target.bounding_box.x1,
                "height_pixels": eval_res.target.bounding_box.y2 - eval_res.target.bounding_box.y1,
            }

            table_coords = getattr(orig_obj, "table_coordinates", None)
            if table_coords is None and table_calibrator is not None:
                table_coords = table_calibrator.pixel_to_table(orig_obj.center.x, orig_obj.center.y)
            table_coords_dict = table_coords.to_dict() if hasattr(table_coords, "to_dict") else (table_coords if isinstance(table_coords, dict) else None)

            table_dims = getattr(orig_obj, "table_dimensions", None)
            if table_dims is None and table_calibrator is not None:
                table_dims = table_calibrator.estimate_dimensions_mm(
                    orig_obj.bounding_box.width, orig_obj.bounding_box.height
                )
            table_dims_dict = table_dims.to_dict() if hasattr(table_dims, "to_dict") else (table_dims if isinstance(table_dims, dict) else None)

            return MatchResult(
                matched=True,
                matched_object=orig_obj,
                match_score=eval_res.target.confidence,
                requested_object=query.model_dump(),
                image_coordinates=image_coords,
                table_coordinates=table_coords_dict,
                table_dimensions=table_dims_dict,
                coordinate_frame="IMAGE_COORDINATES_PIXELS",
                table_coordinate_frame="TABLE_COORDINATES",
                robot_coordinates_status="UNAVAILABLE_PENDING_CALIBRATION (Physical camera required for 3D extrinsic matrix)",
                reasoning=eval_res.reason,
            )
        else:
            return MatchResult(
                matched=False,
                matched_object=None,
                match_score=0.0,
                requested_object=query.model_dump(),
                image_coordinates=None,
                table_coordinates=None,
                table_dimensions=None,
                coordinate_frame="IMAGE_COORDINATES_PIXELS",
                table_coordinate_frame="TABLE_COORDINATES",
                robot_coordinates_status="UNAVAILABLE_PENDING_CALIBRATION",
                reasoning=eval_res.reason,
            )

    def _extract_query(
        self, task_or_query: Union[StructuredTask, ObjectMatchQuery, Dict[str, Any]]
    ) -> ObjectMatchQuery:
        if isinstance(task_or_query, ObjectMatchQuery):
            return task_or_query
        if isinstance(task_or_query, dict):
            return ObjectMatchQuery(**task_or_query)
        if isinstance(task_or_query, StructuredTask):
            obj = task_or_query.object
            color = obj.color if obj and obj.color else (obj.attributes.color if obj and obj.attributes else None)
            return ObjectMatchQuery(
                name=obj.name if obj else None,
                color=color,
                attributes=obj.attributes.model_dump() if obj and obj.attributes else {},
            )
        return ObjectMatchQuery()

    def _are_synonyms(self, query_name: str, detected_name: str) -> bool:
        synonyms = self.SYNONYM_MAP.get(query_name, [query_name])
        return detected_name in synonyms


# Singleton matcher
object_matcher = ObjectMatcher()
