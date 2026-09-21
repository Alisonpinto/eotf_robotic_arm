# ROBOT-AI: Full-Stack AI Robotic-Arm Control Platform

A modern full-stack platform designed to orchestrate two 6-DOF robotic arms:
1. **Custom DIY 3D-Printed Robotic Arm** (Hybrid Stepper/Servo with Forward Kinematics)
2. **Hiwonder JetArm** (Smart Bus Servos with Jetson Vision & Kinematics)

Physical hardware drivers are decoupled via a clean hardware abstraction layer (`RobotArmInterface`), allowing high-fidelity simulation twins now and plug-and-play real hardware drivers later without altering frontend or backend architectures.

---

## Architecture Overview

```
robot-ai/
├── frontend/                     # Next.js 16 (App Router) + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx          # Master Cyber Robotics Dashboard
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── Header.tsx        # Vitals, Connectivity, Simulation Twin, E-Stop
│   │   │   ├── RobotCard.tsx     # 6-DOF Joint Telemetry, Pose, Gripper, Health
│   │   │   ├── VisionFeed.tsx    # Live OpenCV MJPEG video feed & HUD detections
│   │   │   ├── CommandInput.tsx  # Natural-Language Console & 4-Stage Pipeline
│   │   │   └── TaskLogPanel.tsx  # Asynchronous Task Progress & Scrolling Logs
│   │   ├── lib/
│   │   │   └── api.ts            # REST API Client
│   │   └── types/
│   │       └── index.ts          # TypeScript interfaces (StructuredTask, etc.)
│   └── package.json
├── backend/                      # Python 3.10+ & FastAPI
│   ├── main.py                   # Server entrypoint & WebSocket telemetry
│   ├── requirements.txt          # Backend dependencies
│   ├── api/                      # REST routers (Robots, Command, Tasks, Vision)
│   ├── ai/                       # Dynamic Natural-Language Parser (StructuredTask)
│   │   ├── interpreter.py        # parse_command(user_command) interface
│   │   └── schemas.py            # Pydantic Schemas (ObjectAttributes, TargetObject)
│   ├── vision/                   # OpenCV Processor (MJPEG stream & detection)
│   ├── robots/                   # Hardware Abstraction Layer
│   │   ├── base.py               # RobotArmInterface (ABC)
│   │   ├── diy_arm.py            # DIYArmController (6-DOF simulation + serial hooks)
│   │   ├── jetarm.py             # JetArmController (6-DOF simulation + SDK hooks)
│   │   └── manager.py            # RobotManager registry singleton
│   ├── tasks/                    # Asynchronous Task Runner & Step Tracking
│   └── test_backend.py           # Automated verification test suite
├── README.md
└── .gitignore
```

---

## Dynamic Natural-Language Command Interpretation

The platform accepts arbitrary natural-language instructions without relying on a database or rigid hardcoded phrases.

### Python Interface:
```python
from ai.interpreter import parse_command

task = parse_command("Pick the red bottle and give it to the JetArm.")
print(task.model_dump_json(indent=2))
```

### Output Schema (`StructuredTask`):
```json
{
  "raw_command": "Pick the red bottle and give it to the JetArm.",
  "action": "pick_and_transfer",
  "object": {
    "name": "bottle",
    "attributes": {
      "color": "red",
      "size": null,
      "shape": null,
      "extra": {}
    },
    "quantity": 1
  },
  "source": "diy_arm",
  "destination": "jetarm",
  "confidence": 0.96,
  "summary": "Action [pick_and_transfer] on 'red bottle' by diy_arm -> jetarm"
}
```

### Visual Pipeline Display:
Whenever a command is executed in the web console, the frontend immediately renders the 4-stage breakdown:
1. **User command**
   $$\downarrow$$
2. **Interpreted task** (`action`, `source`, `destination`)
   $$\downarrow$$
3. **Extracted object** (`name`, `attributes`, `quantity`)
   $$\downarrow$$
4. **Action** (`dispatched plan steps`)

---

## Getting Started Locally

### 1. Prerequisites
- Python 3.10+
- Node.js v18+ (tested on Node v22)
- npm v9+

---

### 2. Running the FastAPI Backend

Open a terminal and navigate to `backend/`:

```powershell
cd robot-ai/backend
```

Install dependencies (if not already installed):
```powershell
pip install -r requirements.txt
```

Run the backend server:
```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The backend will be available at:
- **API Base**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **Vision Stream**: `http://127.0.0.1:8000/api/vision/stream`

To run the automated verification suite:
```powershell
python test_backend.py
```

---

### 3. Running the Next.js Frontend

Open a second terminal and navigate to `frontend/`:

```powershell
cd robot-ai/frontend
```

Install dependencies:
```powershell
npm install
```

Start the development server:
```powershell
npm run dev
```

Or build and run the optimized production bundle:
```powershell
npm run build
npm start
```

Open your browser at:
`http://localhost:3000`

---

## Computer Vision & Real-Time Camera Subsystem

The platform features an extensible computer vision pipeline with real-time camera streaming, deep neural network object detection, and color attribute extraction.

### 1. Camera Architecture & Pluggable Sources

Camera input is decoupled through an abstract base class hierarchy:

```
CameraSource (ABC)
├── WebcamCamera         # Laptop built-in webcam (index 0) or USB camera via OpenCV
├── VideoFileCamera      # Offline recorded video test stream
└── FutureNetworkCamera  # Extensible for phone USB (DroidCam/IP Webcam) & RTSP network cams
```

- **Thread-safe background grabber**: `WebcamCamera` grabs frames in a background worker thread to prevent video buffer buildup and provide low-latency live streaming.
- **Camera Manager**: `camera_manager` coordinates starting, stopping, and switching camera sources without altering downstream detection or robotic task logic.

### 2. Real Object Detection (YOLOv8)

The vision detector uses a real pretrained YOLO model (`yolov8n.pt` from `ultralytics`) capable of detecting everyday objects:
- `mouse`, `bottle`, `cup`, `laptop`, `keyboard`, `person`, `cell phone`, `chair`, `book`, etc.
- No mock or random detection data is generated.
- Falls back gracefully to the OpenCV color/contour detector if the neural network is unavailable.

### 3. OpenCV Dominant Color Estimation

Each detected bounding box is cropped, filtered against background margins, and evaluated in HSV color space to assign semantic color attributes (`red`, `green`, `blue`, `yellow`, `orange`, `purple`, `black`, `white`, `gray`).

Structured Detection Output:
```json
{
  "id": "obj_f00912",
  "name": "mouse",
  "color": "black",
  "confidence": 0.94,
  "bounding_box": {
    "x1": 120,
    "y1": 180,
    "x2": 260,
    "y2": 300
  },
  "center": {
    "x": 190,
    "y": 240
  },
  "coordinate_frame": "IMAGE_COORDINATES_PIXELS",
  "robot_coordinates": null
}
```

### 4. Critical Distinction: Camera Coordinates vs. Robot Coordinates

> **IMPORTANT**:
> - Coordinates returned by the vision system are strictly **IMAGE PIXEL COORDINATES** ($[0..W, 0..H]$).
> - **Camera coordinates $\neq$ Robot coordinates**.
> - Robot Cartesian coordinates ($X, Y, Z$ in millimeters) remain `null` / pending calibration until physical camera extrinsic transformation matrices ($[K | R | t]$) are calculated with the physical robotic arm.

### 5. Running Vision Tests

Run the camera abstraction, color estimator, and laptop webcam detection test suite:
```powershell
python test_camera.py
```

---

## Hardware Extension Guide

When physical hardware is ready:

1. **Custom DIY 3D-Printed Arm**:
   - Open [`backend/robots/diy_arm.py`](file:///c:/Users/Dell/Desktop/Eotf_robot_software/robot-ai/backend/robots/diy_arm.py)
   - Set `self._simulation = False`
   - In `connect()`, initialize PySerial connection to Arduino/ESP32 (e.g. `serial.Serial("COM3", 115200)`)
   - In `move_joints()`, stream G-code or joint angles to the microcontroller.

2. **Hiwonder JetArm**:
   - Open [`backend/robots/jetarm.py`](file:///c:/Users/Dell/Desktop/Eotf_robot_software/robot-ai/backend/robots/jetarm.py)
   - Set `self._simulation = False`
   - In `connect()`, initialize the Hiwonder JetArm Python SDK or Rosmaster bus servo controller
   - In `move_joints()`, call `arm.set_servo_angle()`.
