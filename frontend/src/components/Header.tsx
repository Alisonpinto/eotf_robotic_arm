'use client';

import React from 'react';
import { Activity, AlertOctagon, Cpu, Home, ShieldAlert, Wifi, WifiOff } from 'lucide-react';

interface HeaderProps {
  isConnected: boolean;
  isSimulated: boolean;
  onEmergencyStop: () => void;
  onHomeAll: () => void;
  isEstopActive?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  isConnected,
  isSimulated,
  onEmergencyStop,
  onHomeAll,
  isEstopActive = false,
}) => {
  return (
    <header className="border-b border-cyan-900/40 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50 px-4 lg:px-8 py-3 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand and Mission Identity */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-2.5">
            <div className="h-10 w-10 rounded-lg bg-cyan-950/60 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
              <Cpu className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-black tracking-widest bg-gradient-to-r from-cyan-400 via-sky-200 to-indigo-400 bg-clip-text text-transparent uppercase font-mono">
                  ROBOT-AI
                </span>
                <span className="text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-700/50 uppercase">
                  v1.0 Core
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono tracking-tight">
                Dual 6-DOF Arm Control Center • DIY Arm & JetArm
              </p>
            </div>
          </div>

          {/* Mobile indicator */}
          <div className="flex items-center gap-2 md:hidden">
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border ${
                isConnected
                  ? 'bg-emerald-950/60 text-emerald-400 border-emerald-500/40'
                  : 'bg-rose-950/60 text-rose-400 border-rose-500/40'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-ping' : 'bg-rose-400'}`} />
              {isConnected ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {/* Global Controls & Status Badges */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
          {/* Status Badges */}
          <div className="hidden md:flex items-center gap-2.5 font-mono text-xs">
            {/* Simulation Twin Badge */}
            {isSimulated && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-amber-950/40 text-amber-300 border border-amber-500/30">
                <Activity className="w-3.5 h-3.5 text-amber-400" />
                <span>SIMULATION TWIN</span>
              </span>
            )}

            {/* Connection Status */}
            <span
              className={`inline-flex items-center gap-2 px-3 py-1 rounded border transition-colors ${
                isConnected
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30'
                  : 'bg-rose-950/40 text-rose-300 border-rose-500/30'
              }`}
            >
              {isConnected ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    BACKEND CONNECTED
                  </span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-rose-400" />
                  <span>DISCONNECTED</span>
                </>
              )}
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={onHomeAll}
              disabled={!isConnected}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700/60 hover:border-cyan-500/50 text-xs font-mono tracking-wider transition-all disabled:opacity-40"
              title="Return both robotic arms to home calibration poses"
            >
              <Home className="w-3.5 h-3.5 text-cyan-400" />
              <span>HOME ALL</span>
            </button>

            {/* Prominent Emergency Stop Button */}
            <button
              onClick={onEmergencyStop}
              disabled={!isConnected}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-mono font-bold text-xs tracking-wider transition-all shadow-lg ${
                isEstopActive
                  ? 'bg-rose-600 text-white animate-bounce shadow-rose-600/50 border border-rose-400'
                  : 'bg-gradient-to-r from-rose-700 via-red-600 to-rose-700 hover:from-rose-600 hover:to-red-500 text-white border border-rose-400/50 shadow-red-900/40 hover:shadow-red-600/60 active:scale-95'
              }`}
              title="EMERGENCY STOP: Halts all arm motors immediately"
            >
              <AlertOctagon className="w-4 h-4 text-white" />
              <span>{isEstopActive ? 'ESTOP ENGAGED' : 'EMERGENCY STOP'}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
