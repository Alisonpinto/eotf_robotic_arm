export type ConnectionState = 'SIMULATED' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR';
export type RobotOperatingMode = 'IDLE' | 'MANUAL' | 'RUNNING_TASK' | 'ESTOP' | 'ERROR';

export interface JointAngles {
  j1: number;
  j2: number;
  j3: number;
  j4: number;
  j5: number;
  j6: number;
}

export interface Pose3D {
  x: number;
  y: number;
  z: number;
  roll: number;
  pitch: number;
  yaw: number;
}

export interface GripperState {
  position: number; // 0 to 100
  state: 'OPEN' | 'CLOSED' | 'MOVING' | 'GRIPPING';
}

export interface RobotStatus {
  id: string;
  name: string;
  arm_type: string;
  connection: ConnectionState;
  mode: RobotOperatingMode;
  joints: JointAngles;
  pose: Pose3D;
  gripper: GripperState;
  voltage: number;
  temperature: number;
  current_load_pct: number;
  error_message?: string | null;
  updated_at: number;
}

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Point2D {
  x: number;
  y: number;
}

export interface TableCoordinates {
  x: number;
  y: number;
  z: number;
  frame: string;
  unit: string;
  is_placeholder_calibration?: boolean;
}

export interface TableDimensions {
  width_mm: number;
  length_mm: number;
  pixel_width: number;
  pixel_height: number;
  unit: string;
}

export interface DetectedObject {
  id: string;
  name: string;
  confidence: number;
  bounding_box: BoundingBox;
  center: Point2D;
  color?: string | null;
  area_pixels?: number;
  coordinate_frame?: string;
  table_coordinates?: TableCoordinates | null;
  table_dimensions?: TableDimensions | null;
  robot_coordinates?: any;
}

export interface MatchResult {
  matched: boolean;
  matched_object?: DetectedObject | null;
  match_score: number;
  requested_object?: Record<string, any>;
  image_coordinates?: {
    center: Point2D;
    bounding_box: BoundingBox;
    width_pixels: number;
    height_pixels: number;
  } | null;
  table_coordinates?: TableCoordinates | null;
  table_dimensions?: TableDimensions | null;
  coordinate_frame: string;
  table_coordinate_frame?: string;
  robot_coordinates_status: string;
  reasoning: string;
}

export interface DetectionResponse {
  status: string;
  image_width: number;
  image_height: number;
  detected_objects: DetectedObject[];
  match_result?: MatchResult | null;
  coordinate_system: string;
  table_coordinate_system?: string;
  table_surface_z_mm?: number;
  is_placeholder_calibration?: boolean;
  robot_coordinate_status: string;
}

export interface ObjectAttributes {
  color?: string | null;
  size?: string | null;
  shape?: string | null;
  extra?: Record<string, any>;
}

export interface TargetObject {
  name: string;
  color?: string | null;
  colour?: string | null;
  attributes: ObjectAttributes;
  quantity?: number | string | null;
}

export interface StructuredTask {
  raw_command: string;
  action: string;
  object?: TargetObject | null;
  object_name?: string | null;
  colour?: string | null;
  color?: string | null;
  source_robot?: string | null;
  destination_robot?: string | null;
  source?: string | null;
  destination?: string | null;
  confidence: number;
  summary: string;
}

export interface RobotAction {
  action_id: string;
  action_type: string;
  robot_id: string;
  parameters: Record<string, any>;
  description: string;
  estimated_duration_sec: number;
}

export interface ActionPlan {
  plan_id: string;
  raw_command: string;
  intent: string;
  target_robot: string;
  structured_task?: StructuredTask | null;
  actions: RobotAction[];
  confidence: number;
  explanation: string;
  created_at: number;
}

export type TaskState = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type LogLevel = 'INFO' | 'STEP' | 'SUCCESS' | 'WARN' | 'ERROR';

export interface TaskLogEntry {
  timestamp: number;
  formatted_time: string;
  level: LogLevel;
  message: string;
}

export interface TaskRecord {
  task_id: string;
  plan: ActionPlan;
  structured_task?: StructuredTask | null;
  state: TaskState;
  progress_pct: number;
  current_step_index: number;
  total_steps: number;
  current_step_desc: string;
  logs: TaskLogEntry[];
  created_at: number;
  started_at?: number | null;
  completed_at?: number | null;
  error?: string | null;
}

export interface SystemStatus {
  status: string;
  platform: string;
  simulation_mode: boolean;
  robots_online: number;
  active_task_id?: string | null;
  system_time: number;
}

export interface CameraStatus {
  source_type: string;
  device_index?: number;
  is_running: boolean;
  fps: number;
  stream_fps?: number;
  frame_count?: number;
  width?: number;
  height?: number;
  last_error?: string | null;
  active_detections_count?: number;
}

export interface CameraActionResponse {
  success: boolean;
  status: string;
  message: string;
  camera_status: CameraStatus;
}

export interface MatchedTarget {
  name: string;
  color?: string | null;
  confidence: number;
  bounding_box: BoundingBox;
  center: Point2D;
  coordinate_frame: string;
  table_coordinates?: TableCoordinates | null;
  table_dimensions?: TableDimensions | null;
  robot_coordinates?: any;
}

export interface CommandMatchResponse {
  status: string;
  understanding: string;
  task: StructuredTask;
  found: boolean;
  target?: MatchedTarget | null;
  candidates: MatchedTarget[];
  ambiguous: boolean;
  reason: string;
  camera_active: boolean;
}
