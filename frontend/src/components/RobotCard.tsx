'use client';

import React, { useState } from 'react';
import { RobotStatus } from '@/types';
import {
  Compass,
  Crosshair,
  Gauge,
  Home,
  Layers,
  Power,
  RotateCcw,
  Sparkles,
  Thermometer,
  Zap,
} from 'lucide-react';
import { homeRobot, setGripper, emergencyStopRobot } from '@/lib/api';

interface RobotCardProps {
  robot: RobotStatus;
  accentColor?: 'cyan' | 'amber' | 'emerald';
  onRefresh?: () => void;
}

export const RobotCard: React.FC<RobotCardProps> = ({
  robot,
  accentColor = 'cyan',
  onRefresh,
}) => {
  const [loadingAction, setLoadingAction] = useState<string | null>(null);

  const isEstop = robot.mode === 'ESTOP';
  const isMoving = robot.mode === 'MANUAL' || robot.mode === 'RUNNING_TASK';

  const handleHome = async () => {
    setLoadingAction('home');
    try {
      await homeRobot(robot.id);
      onRefresh?.();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAction(null);
    }
  };

  const handleGripper = async (position: number) => {
    setLoadingAction(`gripper-${position}`);
    try {
      await setGripper(robot.id, position);
      onRefresh?.();
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAction(null);
    }
  };

  const jointNames: Array<{ key: keyof typeof robot.joints; label: string; min: number; max: number }> = [
    { key: 'j1', label: 'J1 (Base)', min: -180, max: 180 },
    { key: 'j2', label: 'J2 (Shoulder)', min: -90, max: 90 },
    { key: 'j3', label: 'J3 (Elbow)', min: -135, max: 135 },
    { key: 'j4', label: 'J4 (Pitch)', min: -90, max: 90 },
    { key: 'j5', label: 'J5 (Roll)', min: -180, max: 180 },
    { key: 'j6', label: 'J6 (Yaw)', min: -180, max: 180 },
  ];

  return (
    <div
      className={`relative rounded-xl border bg-slate-900/60 backdrop-blur-md p-5 transition-all shadow-xl ${
        isEstop
          ? 'border-rose-500/70 shadow-rose-950/30'
          : accentColor === 'cyan'
          ? 'border-cyan-500/30 shadow-cyan-950/20 hover:border-cyan-500/50'
          : 'border-amber-500/30 shadow-amber-950/20 hover:border-amber-500/50'
      }`}
    >
      {/* Header Info */}
      <div className="flex items-start justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-100 font-mono tracking-tight">
              {robot.name}
            </h3>
            <span
              className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold tracking-wider ${
                robot.id === 'jetarm'
                  ? 'bg-amber-950/80 text-amber-300 border border-amber-500/40'
                  : 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/40'
              }`}
            >
              {robot.id.toUpperCase()}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">{robot.arm_type}</p>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-1.5 font-mono">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold tracking-wider border ${
              isEstop
                ? 'bg-rose-950/90 text-rose-300 border-rose-500 animate-pulse'
                : isMoving
                ? 'bg-indigo-950/80 text-indigo-300 border-indigo-500 animate-pulse'
                : 'bg-emerald-950/60 text-emerald-300 border-emerald-500/40'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isEstop ? 'bg-rose-400' : isMoving ? 'bg-indigo-400 animate-ping' : 'bg-emerald-400'
              }`}
            />
            {robot.mode}
          </span>
        </div>
      </div>

      {/* 6-DOF Joint Angles Telemetry */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs font-mono text-slate-300 mb-2">
          <span className="flex items-center gap-1.5 text-cyan-400 font-semibold tracking-wider uppercase">
            <Compass className="w-3.5 h-3.5" /> 6-DOF Joint Telemetry
          </span>
          <span className="text-[11px] text-slate-500">Angle Range</span>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          {jointNames.map(({ key, label, min, max }) => {
            const angle = robot.joints[key] ?? 0;
            const pct = Math.min(100, Math.max(0, ((angle - min) / (max - min)) * 100));

            return (
              <div
                key={key}
                className="bg-slate-950/60 rounded-lg p-2.5 border border-slate-800/80 hover:border-slate-700/80 transition-all font-mono"
              >
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-slate-400 font-medium">{label}</span>
                  <span className="text-cyan-300 font-bold tracking-tight">
                    {angle > 0 ? `+${angle.toFixed(1)}` : angle.toFixed(1)}°
                  </span>
                </div>
                {/* Visual Bar */}
                <div className="w-full bg-slate-800/80 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 rounded-full transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex justify-between text-[9px] text-slate-500 mt-1">
                  <span>{min}°</span>
                  <span>{max}°</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Cartesian Pose & Gripper Gauges */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* End Effector Pose */}
        <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/80 font-mono">
          <div className="flex items-center gap-1.5 text-xs text-sky-400 font-semibold tracking-wider uppercase mb-2">
            <Crosshair className="w-3.5 h-3.5" /> End-Effector Pose
          </div>
          <div className="grid grid-cols-3 gap-1.5 text-xs">
            <div className="bg-slate-900/80 rounded px-2 py-1 text-center border border-slate-800">
              <span className="text-[10px] text-slate-500 block">X</span>
              <span className="text-slate-200 font-bold">{robot.pose.x}</span>
              <span className="text-[9px] text-slate-500 ml-0.5">mm</span>
            </div>
            <div className="bg-slate-900/80 rounded px-2 py-1 text-center border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Y</span>
              <span className="text-slate-200 font-bold">{robot.pose.y}</span>
              <span className="text-[9px] text-slate-500 ml-0.5">mm</span>
            </div>
            <div className="bg-slate-900/80 rounded px-2 py-1 text-center border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Z</span>
              <span className="text-slate-200 font-bold">{robot.pose.z}</span>
              <span className="text-[9px] text-slate-500 ml-0.5">mm</span>
            </div>
          </div>
        </div>

        {/* Gripper Actuator */}
        <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/80 font-mono">
          <div className="flex items-center justify-between text-xs text-emerald-400 font-semibold tracking-wider uppercase mb-2">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5" /> Gripper Claw
            </span>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-600/40">
              {robot.gripper.state}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-slate-400">Position</span>
            <span className="text-emerald-300 font-bold">{robot.gripper.position.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-300"
              style={{ width: `${robot.gripper.position}%` }}
            />
          </div>
        </div>
      </div>

      {/* Hardware Telemetry Vitals */}
      <div className="flex items-center justify-between bg-slate-950/80 rounded-lg px-3 py-2 border border-slate-800/80 text-xs font-mono text-slate-400 mb-4">
        <div className="flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          <span>{robot.voltage.toFixed(2)} V</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Thermometer className="w-3.5 h-3.5 text-rose-400" />
          <span>{robot.temperature.toFixed(1)} °C</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Gauge className="w-3.5 h-3.5 text-cyan-400" />
          <span>Load {robot.current_load_pct}%</span>
        </div>
      </div>

      {/* Quick Action Buttons */}
      <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
        <button
          onClick={handleHome}
          disabled={loadingAction !== null || isEstop}
          className="flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-mono tracking-wider transition-all border border-slate-700 disabled:opacity-40"
        >
          <RotateCcw className={`w-3.5 h-3.5 text-cyan-400 ${loadingAction === 'home' ? 'animate-spin' : ''}`} />
          <span>Home</span>
        </button>

        <button
          onClick={() => handleGripper(0)}
          disabled={loadingAction !== null || isEstop}
          className="flex-1 inline-flex items-center justify-center gap-1 py-2 px-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-mono tracking-wider transition-all border border-slate-700 disabled:opacity-40"
        >
          <span>Open Claw</span>
        </button>

        <button
          onClick={() => handleGripper(90)}
          disabled={loadingAction !== null || isEstop}
          className="flex-1 inline-flex items-center justify-center gap-1 py-2 px-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 text-xs font-mono tracking-wider transition-all border border-slate-700 disabled:opacity-40"
        >
          <span>Grip</span>
        </button>
      </div>
    </div>
  );
};
