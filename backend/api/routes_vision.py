import cv2
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

try:
    from vision.processor import vision_processor
    from vision.detector import DetectedObject, vision_detector
    from vision.camera import camera_source, camera_manager
    from vision.object_matcher import object_matcher, MatchResult, ObjectMatchQuery
except ImportError:
    from ..vision.processor import vision_processor
    from ..vision.detector import DetectedObject, vision_detector
    from ..vision.camera import camera_source, camera_manager
    from ..vision.object_matcher import object_matcher, MatchResult, ObjectMatchQuery

router = APIRouter(prefix="/api/vision", tags=["vision"])


class DetectionResponse(BaseModel):
    status: str
    image_width: int
    image_height: int
    detected_objects: List[DetectedObject]
    match_result: Optional[MatchResult] = None
    coordinate_system: str = "IMAGE_COORDINATES_PIXELS"
    robot_coordinate_status: str = "PENDING_CALIBRATION (Extrinsic transformation matrix needed when physical camera is installed)"


class SampleDetectRequest(BaseModel):
    target_name: Optional[str] = None
    target_color: Optional[str] = None


class CameraActionResponse(BaseModel):
    success: bool
    status: str
    message: str
    camera_status: Dict[str, Any]


@router.post("/camera/start", response_model=CameraActionResponse)
async def start_camera():
    """
    Open and start the default physical camera source (laptop webcam, device 0).
    """
    success = vision_processor.start_camera()
    status = vision_processor.get_camera_status()
    if success:
        return CameraActionResponse(
            success=True,
            status="RUNNING",
            message="Laptop webcam started successfully.",
            camera_status=status,
        )
    else:
        return CameraActionResponse(
            success=False,
            status="ERROR",
            message=f"Failed to open camera: {status.get('last_error', 'Unknown hardware error')}",
            camera_status=status,
        )


@router.post("/camera/stop", response_model=CameraActionResponse)
async def stop_camera():
    """
    Stop the camera stream and release camera hardware resources.
    """
    vision_processor.stop_camera()
    status = vision_processor.get_camera_status()
    return CameraActionResponse(
        success=True,
        status="STOPPED",
        message="Camera stopped and resources released.",
        camera_status=status,
    )


@router.get("/camera/status")
async def get_camera_status():
    """
    Retrieve current camera diagnostic status, source type, FPS, and running state.
    """
    return vision_processor.get_camera_status()


@router.get("/stream")
async def video_feed():
    """
    Real-time MJPEG live stream of the robotic workspace camera.
    Directly compatible with HTML <img src="/api/vision/stream" />
    Draws real-time detected objects, bounding boxes, labels, and center coordinates.
    """
    return StreamingResponse(
        vision_processor.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/snapshot")
async def camera_snapshot():
    """Capture a single JPEG snapshot of current workspace."""
    frame_bytes = vision_processor.get_frame_jpeg()
    return Response(content=frame_bytes, media_type="image/jpeg")


@router.get("/detections", response_model=List[DetectedObject])
async def get_active_detections():
    """Get list of active detected objects from the live processor."""
    return vision_processor.get_detections()


@router.post("/detect", response_model=DetectionResponse)
async def detect_uploaded_image(
    file: UploadFile = File(...),
    target_name: Optional[str] = Form(None),
    target_color: Optional[str] = Form(None),
):
    """
    Process an uploaded test image (JPEG/PNG), detect objects using YOLO/OpenCV,
    and optionally match against an AI command target.
    
    Coordinates returned are explicitly in IMAGE PIXEL COORDINATES (x1, y1, x2, y2, center_x, center_y).
    Camera coordinates != Robot coordinates.
    """
    contents = await file.read()
    image = camera_source.load_from_bytes(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode uploaded image.")

    h, w = image.shape[:2]
    detected_objects = vision_detector.detect(image)

    # If target criteria is provided, match against detected objects
    match_res = None
    if target_name or target_color:
        query = ObjectMatchQuery(name=target_name, color=target_color)
        match_res = object_matcher.match(detected_objects, query)

    return DetectionResponse(
        status="success",
        image_width=w,
        image_height=h,
        detected_objects=detected_objects,
        match_result=match_res,
        coordinate_system="IMAGE_COORDINATES_PIXELS",
        robot_coordinate_status="PENDING_CALIBRATION (Requires camera extrinsic calibration matrix [K|R|t])",
    )


@router.post("/detect-sample", response_model=DetectionResponse)
async def detect_sample_image(req: Optional[SampleDetectRequest] = None):
    """
    Generate and analyze the synthetic test workbench containing:
    - Red bottle
    - Blue cup
    - Green box
    - Yellow canister
    """
    sample_img = camera_source.generate_sample_workbench_image()
    h, w = sample_img.shape[:2]
    detected_objects = vision_detector.detect(sample_img)

    match_res = None
    target_name = req.target_name if req else None
    target_color = req.target_color if req else None

    if target_name or target_color:
        query = ObjectMatchQuery(name=target_name, color=target_color)
        match_res = object_matcher.match(detected_objects, query)

    return DetectionResponse(
        status="success",
        image_width=w,
        image_height=h,
        detected_objects=detected_objects,
        match_result=match_res,
        coordinate_system="IMAGE_COORDINATES_PIXELS",
        robot_coordinate_status="PENDING_CALIBRATION (Requires camera extrinsic calibration matrix [K|R|t])",
    )


@router.get("/sample-image")
async def get_sample_image():
    """Download the synthetic test workbench image as a JPEG."""
    sample_img = camera_source.generate_sample_workbench_image()
    ret, buffer = cv2.imencode(".jpg", sample_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ret:
        raise HTTPException(status_code=500, detail="Failed to encode sample image")
    return Response(content=buffer.tobytes(), media_type="image/jpeg")
