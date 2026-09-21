import {
  CommandMatchResponse,
  DetectionResponse,
  CameraActionResponse,
  CameraStatus,
  DetectedObject,
  StructuredTask,
  ActionPlan,
  TaskRecord,
  RobotStatus,
  SystemStatus,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function getVideoStreamUrl(): string {
  return `${API_BASE}/api/vision/stream`;
}

export async function matchCommand(
  command: string,
  preferredRobot?: string,
  useLiveCamera: boolean = true
): Promise<CommandMatchResponse> {
  const res = await fetch(`${API_BASE}/api/command/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      command,
      preferred_robot: preferredRobot,
      use_live_camera: useLiveCamera,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to process command' }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

export async function parseCommand(
  command: string,
  preferredRobot?: string
): Promise<StructuredTask> {
  const res = await fetch(`${API_BASE}/api/command/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      command,
      preferred_robot: preferredRobot,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to parse command' }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

export async function previewCommandPlan(
  command: string,
  preferredRobot?: string
): Promise<ActionPlan> {
  const res = await fetch(`${API_BASE}/api/command/plan_only`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      command,
      preferred_robot: preferredRobot,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to preview plan' }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

export async function executeNaturalCommand(
  command: string,
  preferredRobot?: string
): Promise<TaskRecord> {
  const res = await fetch(`${API_BASE}/api/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      command,
      preferred_robot: preferredRobot,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to execute command' }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

export async function startCamera(): Promise<CameraActionResponse> {
  const res = await fetch(`${API_BASE}/api/vision/camera/start`, {
    method: 'POST',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start camera' }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

export async function stopCamera(): Promise<CameraActionResponse> {
  const res = await fetch(`${API_BASE}/api/vision/camera/stop`, {
    method: 'POST',
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to stop camera' }));
    throw new Error(err.detail || `Server returned ${res.status}`);
  }

  return res.json();
}

export async function fetchCameraStatus(): Promise<CameraStatus> {
  const res = await fetch(`${API_BASE}/api/vision/camera/status`);
  if (!res.ok) {
    throw new Error(`Failed to fetch camera status (${res.status})`);
  }
  return res.json();
}

export async function fetchDetections(): Promise<DetectedObject[]> {
  const res = await fetch(`${API_BASE}/api/vision/detections`);
  if (!res.ok) {
    return [];
  }
  return res.json();
}

export async function fetchRobots(): Promise<RobotStatus[]> {
  const res = await fetch(`${API_BASE}/api/robots`);
  if (!res.ok) {
    return [];
  }
  return res.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) {
    throw new Error('Backend offline');
  }
  return res.json();
}
