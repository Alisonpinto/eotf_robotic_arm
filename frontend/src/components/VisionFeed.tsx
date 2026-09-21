'use client';

import React, { useState, useEffect } from 'react';
import { Camera, Eye, Maximize2, RefreshCw, Scan, Tag } from 'lucide-react';
import { getVideoStreamUrl, fetchDetections } from '@/lib/api';
import { DetectedObject } from '@/types';

interface VisionFeedProps {
  isConnected: boolean;
}

export const VisionFeed: React.FC<VisionFeedProps> = ({ isConnected }) => {
  const [streamUrl, setStreamUrl] = useState<string>('');
  const [detections, setDetections] = useState<DetectedObject[]>([]);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [streamError, setStreamError] = useState<boolean>(false);
  const [showCrosshair, setShowCrosshair] = useState<boolean>(true);

  useEffect(() => {
    if (isConnected) {
      setStreamUrl(getVideoStreamUrl());
      setStreamError(false);
      loadDetections();
    }
  }, [isConnected]);

  // Periodic poll of detections metadata
  useEffect(() => {
    if (!isConnected) return;
    const interval = setInterval(() => {
      loadDetections();
    }, 2000);
    return () => clearInterval(interval);
  }, [isConnected]);

  const loadDetections = async () => {
    try {
      const list = await fetchDetections();
      setDetections(list);
    } catch (e) {
      // ignore
    }
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    setStreamError(false);
    // Add cache buster query parameter
    setStreamUrl(`${getVideoStreamUrl()}?t=${Date.now()}`);
    loadDetections().finally(() => setIsRefreshing(false));
  };

  return (
    <div className="rounded-xl border border-cyan-500/30 bg-slate-900/60 backdrop-blur-md p-4 shadow-xl flex flex-col h-full">
      {/* Feed Header */}
      <div className="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-800 font-mono text-xs">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-700/40">
            <Camera className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-slate-100 tracking-wider">CAM-01: WORKSPACE TOP-DOWN</span>
            <span className="text-[10px] text-slate-400 block font-normal">OpenCV Stream • YOLO Ready</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Crosshair Toggle */}
          <button
            onClick={() => setShowCrosshair(!showCrosshair)}
            className={`px-2 py-1 rounded text-[11px] border transition-all ${
              showCrosshair
                ? 'bg-cyan-950/80 text-cyan-300 border-cyan-500/50'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}
            title="Toggle Reticle Crosshair"
          >
            HUD
          </button>

          {/* Refresh stream */}
          <button
            onClick={handleRefresh}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="Reload Video Stream"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Video Display Box */}
      <div className="relative aspect-video w-full rounded-lg overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center">
        {isConnected && !streamError && streamUrl ? (
          /* Live Stream Image from FastAPI */
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={streamUrl}
            alt="Robotic Workspace Live Stream"
            className="w-full h-full object-cover select-none"
            onError={() => setStreamError(true)}
          />
        ) : (
          /* Placeholder / Offline Slate */
          <div className="flex flex-col items-center justify-center text-center p-6 text-slate-500 font-mono">
            <Eye className="w-10 h-10 mb-2 text-slate-600 animate-pulse" />
            <p className="text-sm font-semibold text-slate-400">CAMERA STREAM STANDBY</p>
            <p className="text-xs mt-1 text-slate-600">
              {isConnected
                ? 'Connecting to OpenCV visual pipeline...'
                : 'Waiting for backend server to start at :8000'}
            </p>
          </div>
        )}

        {/* Live indicator overlay */}
        {isConnected && !streamError && (
          <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-0.5 rounded bg-black/60 backdrop-blur-sm border border-emerald-500/40 text-[10px] font-mono font-bold text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            LIVE 30FPS
          </div>
        )}
      </div>

      {/* Detected Objects HUD Chips */}
      <div className="mt-3 pt-3 border-t border-slate-800 font-mono">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
          <span className="flex items-center gap-1.5 text-cyan-400 font-semibold tracking-wider">
            <Scan className="w-3.5 h-3.5" /> DETECTED OBJECTS ({detections.length})
          </span>
          <span className="text-[10px] text-slate-500">Auto-Tracking</span>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {detections.length > 0 ? (
            detections.map((obj) => (
              <div
                key={obj.id}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-950/80 border border-slate-800 text-[11px] text-slate-200"
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    obj.color === 'red'
                      ? 'bg-rose-500'
                      : obj.color === 'blue'
                      ? 'bg-sky-500'
                      : 'bg-emerald-500'
                  }`}
                />
                <span className="font-semibold">{obj.name}</span>
                <span className="text-cyan-400 font-mono text-[10px]">
                  {Math.round(obj.confidence * 100)}%
                </span>
                {obj.center && (
                  <span className="text-[9px] text-slate-500">
                    [{obj.center.x},{obj.center.y}]
                  </span>
                )}
              </div>
            ))
          ) : (
            <span className="text-xs text-slate-500">No objects identified in visual field</span>
          )}
        </div>
      </div>
    </div>
  );
};
