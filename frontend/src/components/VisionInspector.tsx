'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Camera,
  Eye,
  Info,
  Loader2,
  Play,
  RefreshCw,
  Sparkles,
  Square,
  Video,
  X,
} from 'lucide-react';
import {
  getVideoStreamUrl,
  startCamera,
  stopCamera,
  fetchCameraStatus,
  fetchDetections,
} from '@/lib/api';
import {
  DetectedObject,
  CameraStatus,
} from '@/types';

interface VisionInspectorProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery?: { name?: string; color?: string };
}

export const VisionInspector: React.FC<VisionInspectorProps> = ({
  isOpen,
  onClose,
  initialQuery,
}) => {
  const [liveDetections, setLiveDetections] = useState<DetectedObject[]>([]);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);
  const [isCameraLoading, setIsCameraLoading] = useState<boolean>(false);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [targetName, setTargetName] = useState<string>(initialQuery?.name || 'bottle');
  const [targetColor, setTargetColor] = useState<string>(initialQuery?.color || 'red');
  const [streamError, setStreamError] = useState<boolean>(false);
  const [streamCacheBuster, setStreamCacheBuster] = useState<number>(Date.now());

  useEffect(() => {
    if (initialQuery?.name) setTargetName(initialQuery.name);
    if (initialQuery?.color !== undefined) setTargetColor(initialQuery.color || '');
  }, [initialQuery]);

  // Poll camera status and live detections when modal is open
  const updateCameraStatus = useCallback(async () => {
    try {
      const status = await fetchCameraStatus();
      setCameraStatus(status);
    } catch {
      // ignore
    }
  }, []);

  const updateLiveDetections = useCallback(async () => {
    try {
      const objects = await fetchDetections();
      setLiveDetections(objects);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    updateCameraStatus();

    // Check camera status and detections periodically when modal is open
    const interval = setInterval(() => {
      updateCameraStatus();
      if (cameraStatus?.is_running) {
        updateLiveDetections();
      }
    }, 1200);

    return () => clearInterval(interval);
  }, [isOpen, cameraStatus?.is_running, updateCameraStatus, updateLiveDetections]);

  // Handle Starting Camera
  const handleStartCamera = async () => {
    setIsCameraLoading(true);
    setStreamError(false);
    try {
      const res = await startCamera();
      setCameraStatus(res.camera_status);
      setStreamCacheBuster(Date.now());
      await updateLiveDetections();
    } catch (err: any) {
      alert(`Could not start laptop webcam: ${err.message}`);
    } finally {
      setIsCameraLoading(false);
    }
  };

  // Handle Stopping Camera
  const handleStopCamera = async () => {
    setIsCameraLoading(true);
    try {
      const res = await stopCamera();
      setCameraStatus(res.camera_status);
      setLiveDetections([]);
    } catch (err: any) {
      alert(`Could not stop camera: ${err.message}`);
    } finally {
      setIsCameraLoading(false);
    }
  };

  // Handle matching query
  const activeObjectsList = liveDetections;

  const matchedObject = activeObjectsList.find((obj) => {
    const nameMatch = !targetName || obj.name.toLowerCase().includes(targetName.toLowerCase());
    const colorMatch = !targetColor || (obj.color && obj.color.toLowerCase() === targetColor.toLowerCase());
    return nameMatch && colorMatch;
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      <div className="bg-[#1c1c20] border border-zinc-700/80 rounded-2xl w-full max-w-5xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300">
              <Camera className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                Computer Vision & Real-Time Camera
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/60 font-mono">
                  YOLOv8 + OpenCV Color
                </span>
              </h2>
              <p className="text-xs text-zinc-400">
                Laptop Webcam Input • Live Object Detection • Image Coordinates vs Robot Coordinates
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Camera Controls Bar */}
        <div className="px-6 py-3 bg-zinc-900/70 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Feed Title */}
          <div className="flex items-center gap-2 font-medium text-zinc-300">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-cyan-400">
              <Video className="w-3.5 h-3.5" />
              <span>Live Webcam Feed</span>
            </div>
          </div>

          {/* Camera Controls (Start / Stop / Status) */}
          <div className="flex items-center gap-2">
            {cameraStatus?.is_running ? (
              <button
                onClick={handleStopCamera}
                disabled={isCameraLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800/60 font-medium transition-colors cursor-pointer"
                title="Stop Laptop Webcam"
              >
                {isCameraLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Square className="w-3.5 h-3.5 fill-current" />
                )}
                <span>Stop Camera</span>
              </button>
            ) : (
              <button
                onClick={handleStartCamera}
                disabled={isCameraLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/90 hover:bg-cyan-900 text-cyan-300 border border-cyan-700/60 font-medium transition-colors cursor-pointer"
                title="Start Laptop Built-in Webcam"
              >
                {isCameraLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current" />
                )}
                <span>Start Camera</span>
              </button>
            )}

            {/* Camera Status Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-zinc-950 border border-zinc-800 font-mono text-[11px]">
              <span
                className={`w-2 h-2 rounded-full ${
                  cameraStatus?.is_running
                    ? 'bg-emerald-400 animate-pulse'
                    : 'bg-zinc-600'
                }`}
              />
              <span className="text-zinc-300">
                {cameraStatus?.source_type || 'Webcam'}:
              </span>
              <span
                className={
                  cameraStatus?.is_running
                    ? 'text-emerald-400 font-bold'
                    : 'text-zinc-500'
                }
              >
                {cameraStatus?.is_running
                  ? `Live (${cameraStatus.fps || 30} FPS)`
                  : 'Standby'}
              </span>
            </div>
          </div>
        </div>

        {/* Content Body: Video Feed on left, Detected Objects on right */}
        <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-y-auto">
          {/* Left Column: View Canvas (7 Cols) */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            <div className="relative aspect-[4/3] rounded-xl overflow-hidden bg-black border border-zinc-800 flex items-center justify-center">
              {/* LIVE WEBCAM STREAM VIEW */}
              {cameraStatus?.is_running && !streamError ? (
                <div className="relative w-full h-full flex items-center justify-center bg-black">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`${getVideoStreamUrl()}?t=${streamCacheBuster}`}
                    alt="Laptop Webcam Live Object Detection Stream"
                    className="w-full h-full object-contain select-none"
                    onError={() => setStreamError(true)}
                  />

                  {/* Live Stream Overlay HUD */}
                  <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded bg-black/75 backdrop-blur-sm border border-emerald-500/50 text-[10px] font-mono font-bold text-emerald-400">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    LIVE FEED • REAL-TIME YOLO
                  </div>

                  <button
                    onClick={() => setStreamCacheBuster(Date.now())}
                    className="absolute top-3 right-3 p-1.5 rounded-lg bg-black/70 hover:bg-black/90 text-zinc-400 hover:text-white border border-zinc-700/60 transition-colors"
                    title="Refresh stream connection"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                /* Camera Standby View */
                <div className="flex flex-col items-center justify-center text-center p-8 text-zinc-500 font-mono">
                  <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-3 text-cyan-400">
                    <Video className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-semibold text-zinc-300">
                    LAPTOP WEBCAM STANDBY
                  </p>
                  <p className="text-xs mt-1 text-zinc-500 max-w-xs mb-4 font-sans">
                    The camera is currently inactive. Click &ldquo;Start Camera&rdquo; to open the webcam and begin real-time YOLO object detection.
                  </p>
                  <button
                    onClick={handleStartCamera}
                    disabled={isCameraLoading}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-700/60 text-xs font-semibold transition-all shadow-lg cursor-pointer"
                  >
                    {isCameraLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4 fill-current" />
                    )}
                    <span>Start Camera</span>
                  </button>
                </div>
              )}
            </div>

            {/* Strict Coordinate Frame Warning */}
            <div className="rounded-lg bg-zinc-900/90 border border-zinc-800 p-3 text-xs font-mono text-zinc-400 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-zinc-200">IMAGE COORDINATES (PIXELS):</strong> Values shown are pixel coordinates from the camera sensor plane [X: 0..640, Y: 0..480].
                <br />
                <span className="text-amber-400/90 text-[11px]">
                  ROBOT COORDINATES (Cartesian mm) are pending extrinsic hand-eye calibration matrix once the physical robot arm and camera mount are installed. Camera coordinates != Robot coordinates.
                </span>
              </div>
            </div>
          </div>

          {/* Right Column: Detected Objects & Matcher Results (5 Cols) */}
          <div className="lg:col-span-5 flex flex-col gap-4 overflow-y-auto">
            {/* Target Matcher Query Box */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/90 p-3.5 font-mono text-xs">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-zinc-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  OBJECT MATCHER
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    matchedObject
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-600/50'
                      : 'bg-zinc-800 text-zinc-400'
                  }`}
                >
                  {matchedObject ? 'MATCH CONFIRMED' : 'SEARCHING'}
                </span>
              </div>

              <div className="flex items-center gap-2 mb-2">
                <input
                  type="text"
                  placeholder="Target color"
                  value={targetColor}
                  onChange={(e) => setTargetColor(e.target.value)}
                  className="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-zinc-200 focus:outline-none focus:border-zinc-600"
                />
                <input
                  type="text"
                  placeholder="Target name"
                  value={targetName}
                  onChange={(e) => setTargetName(e.target.value)}
                  className="flex-1 bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-xs text-zinc-200 focus:outline-none focus:border-zinc-600"
                />
              </div>

              {matchedObject && (
                <div className="bg-black/50 rounded-lg p-2 border border-emerald-900/60 text-[11px] space-y-1.5">
                  <div className="text-emerald-300 font-semibold flex items-center justify-between">
                    <span>Target: {matchedObject.color || ''} {matchedObject.name}</span>
                    <span className="text-cyan-400 font-bold">{Math.round(matchedObject.confidence * 100)}%</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[10px]">
                    <div>
                      <span className="text-zinc-400">Pixel (u, v):</span>{' '}
                      <strong className="text-white">X:{matchedObject.center.x}, Y:{matchedObject.center.y} px</strong>
                    </div>
                    {matchedObject.table_coordinates && (
                      <div>
                        <span className="text-amber-400">Table (X,Y,Z):</span>{' '}
                        <strong className="text-amber-200">
                          {matchedObject.table_coordinates.x}, {matchedObject.table_coordinates.y}, {matchedObject.table_coordinates.z} mm
                        </strong>
                      </div>
                    )}
                  </div>
                  <div className="text-zinc-400 text-[10px] flex items-center justify-between border-t border-zinc-800/60 pt-1">
                    <span>Box: [{matchedObject.bounding_box.x1}, {matchedObject.bounding_box.y1}, {matchedObject.bounding_box.x2}, {matchedObject.bounding_box.y2}]</span>
                    <span>
                      {matchedObject.bounding_box.x2 - matchedObject.bounding_box.x1} x {matchedObject.bounding_box.y2 - matchedObject.bounding_box.y1} px
                      {matchedObject.table_dimensions && ` (~${matchedObject.table_dimensions.width_mm}x${matchedObject.table_dimensions.length_mm} mm)`}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* List of Real-time Detected Objects */}
            <div>
              <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-2">
                <span className="flex items-center gap-1.5 text-cyan-400 font-semibold">
                  <Eye className="w-3.5 h-3.5" />
                  DETECTED OBJECTS ({activeObjectsList.length})
                </span>
                <span className="text-[10px] text-zinc-500">
                  {cameraStatus?.is_running ? 'Updating live...' : 'Standby'}
                </span>
              </div>

              <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
                {activeObjectsList.length > 0 ? (
                  activeObjectsList.map((obj) => {
                    const isSelected = obj.id === selectedObjectId;
                    const isTargetMatch = matchedObject?.id === obj.id;

                    return (
                      <div
                        key={obj.id}
                        onClick={() => setSelectedObjectId(obj.id)}
                        className={`rounded-xl p-3 border font-mono text-xs cursor-pointer transition-all ${
                          isTargetMatch
                            ? 'bg-emerald-950/30 border-emerald-500/50 shadow-sm'
                            : isSelected
                            ? 'bg-zinc-800/90 border-zinc-500'
                            : 'bg-zinc-900/70 border-zinc-800 hover:border-zinc-700'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span
                              className={`w-2.5 h-2.5 rounded-full ${
                                obj.color === 'red'
                                  ? 'bg-rose-500'
                                  : obj.color === 'blue'
                                  ? 'bg-sky-500'
                                  : obj.color === 'green'
                                  ? 'bg-emerald-500'
                                  : obj.color === 'yellow'
                                  ? 'bg-amber-400'
                                  : obj.color === 'black'
                                  ? 'bg-zinc-800 border border-zinc-600'
                                  : 'bg-cyan-400'
                              }`}
                            />
                            <span className="font-bold text-sm text-zinc-100 capitalize">
                              {obj.name}
                            </span>
                            {obj.color && (
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-950 text-zinc-300 border border-zinc-800">
                                {obj.color}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-1.5">
                            {isTargetMatch && (
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-600/40">
                                MATCH
                              </span>
                            )}
                            <span className="text-xs font-bold text-cyan-400">
                              {Math.round(obj.confidence * 100)}%
                            </span>
                          </div>
                        </div>

                        {/* Coordinates Details: Pixel X/Y, Table X/Y/Z, Dimensions */}
                        <div className="space-y-1.5 text-[11px] text-zinc-300 pt-1.5 border-t border-zinc-800/60">
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <span className="text-zinc-500 block text-[10px]">Pixel Center (u, v)</span>
                              <strong>X: {obj.center.x}, Y: {obj.center.y} px</strong>
                            </div>
                            {obj.table_coordinates && (
                              <div>
                                <span className="text-amber-400 block text-[10px]">Table Surface (X, Y, Z)</span>
                                <strong className="text-amber-200">
                                  X: {obj.table_coordinates.x}, Y: {obj.table_coordinates.y}, Z: {obj.table_coordinates.z} mm
                                </strong>
                              </div>
                            )}
                          </div>

                          <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-zinc-800/40">
                            <span>Box: [{obj.bounding_box.x1}, {obj.bounding_box.y1}, {obj.bounding_box.x2}, {obj.bounding_box.y2}]</span>
                            <span>
                              Dims: {obj.bounding_box.x2 - obj.bounding_box.x1}x{obj.bounding_box.y2 - obj.bounding_box.y1} px
                              {obj.table_dimensions && (
                                <span className="text-zinc-300 ml-1">
                                  (~{obj.table_dimensions.width_mm}x{obj.table_dimensions.length_mm} mm)
                                </span>
                              )}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-8 text-zinc-500 text-xs font-mono">
                    {cameraStatus?.is_running
                      ? 'No objects detected in visual frame.'
                      : 'Webcam is standby. Click "Start Camera" to test live detection.'}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
