'use client';

import React, { useRef, useEffect } from 'react';
import { CheckCircle2, Clock, PlayCircle, Terminal, XCircle, AlertTriangle, X } from 'lucide-react';
import { TaskRecord } from '@/types';
import { cancelTask } from '@/lib/api';

interface TaskLogPanelProps {
  activeTask: TaskRecord | null;
  recentTasks: TaskRecord[];
  onTaskCancelled?: () => void;
}

export const TaskLogPanel: React.FC<TaskLogPanelProps> = ({
  activeTask,
  recentTasks,
  onTaskCancelled,
}) => {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs as new entries arrive
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeTask?.logs]);

  const handleCancel = async (taskId: string) => {
    try {
      await cancelTask(taskId);
      onTaskCancelled?.();
    } catch (e) {
      console.error(e);
    }
  };

  const getLogBadge = (level: string) => {
    switch (level) {
      case 'STEP':
        return 'text-sky-400 bg-sky-950/80 border-sky-600/40';
      case 'SUCCESS':
        return 'text-emerald-400 bg-emerald-950/80 border-emerald-600/40';
      case 'WARN':
        return 'text-amber-400 bg-amber-950/80 border-amber-600/40';
      case 'ERROR':
        return 'text-rose-400 bg-rose-950/80 border-rose-600/40';
      case 'INFO':
      default:
        return 'text-slate-400 bg-slate-800/80 border-slate-700';
    }
  };

  // If there's an active task, show its logs. Otherwise, show the most recent task's logs.
  const displayTask = activeTask || recentTasks[0] || null;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-5 shadow-xl flex flex-col h-full font-mono">
      {/* Panel Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-slate-800 text-cyan-400 border border-slate-700">
            <Terminal className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-200 tracking-wider">
              TASK PROGRESS & EXECUTION LOGS
            </h3>
            <span className="text-[10px] text-slate-500">
              Real-time asynchronous robotic dispatch
            </span>
          </div>
        </div>

        {/* Task State Badge */}
        {displayTask && (
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold border ${
                displayTask.state === 'RUNNING'
                  ? 'bg-sky-950/80 text-sky-300 border-sky-500 animate-pulse'
                  : displayTask.state === 'COMPLETED'
                  ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500'
                  : displayTask.state === 'CANCELLED'
                  ? 'bg-amber-950/80 text-amber-300 border-amber-500'
                  : displayTask.state === 'FAILED'
                  ? 'bg-rose-950/80 text-rose-300 border-rose-500'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              {displayTask.state === 'RUNNING' && <PlayCircle className="w-3 h-3 text-sky-400" />}
              {displayTask.state === 'COMPLETED' && <CheckCircle2 className="w-3 h-3 text-emerald-400" />}
              {displayTask.state === 'CANCELLED' && <AlertTriangle className="w-3 h-3 text-amber-400" />}
              {displayTask.state === 'FAILED' && <XCircle className="w-3 h-3 text-rose-400" />}
              <span>{displayTask.state}</span>
            </span>

            {activeTask && (
              <button
                onClick={() => handleCancel(activeTask.task_id)}
                className="px-2 py-0.5 rounded bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-600/40 text-[10px] flex items-center gap-1 transition-colors"
                title="Abort current task"
              >
                <X className="w-3 h-3" /> Abort
              </button>
            )}
          </div>
        )}
      </div>

      {/* Active Step & Progress Bar */}
      {displayTask ? (
        <div className="mb-3 bg-slate-950/80 rounded-lg p-3 border border-slate-800">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-slate-300 font-semibold truncate max-w-md">
              {displayTask.current_step_desc}
            </span>
            <span className="text-cyan-400 font-bold ml-2">
              {displayTask.progress_pct.toFixed(0)}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                displayTask.state === 'COMPLETED'
                  ? 'bg-emerald-500'
                  : displayTask.state === 'FAILED'
                  ? 'bg-rose-500'
                  : 'bg-gradient-to-r from-cyan-500 via-sky-400 to-indigo-500'
              }`}
              style={{ width: `${displayTask.progress_pct}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1.5">
            <span>Task ID: {displayTask.task_id}</span>
            <span>
              Step {displayTask.current_step_index} / {displayTask.total_steps}
            </span>
          </div>
        </div>
      ) : (
        <div className="mb-3 bg-slate-950/50 rounded-lg p-3 border border-slate-800 text-center text-xs text-slate-500">
          No active or previous robotic tasks recorded. Send a natural-language command above to begin.
        </div>
      )}

      {/* Scrolling Terminal Output */}
      <div className="flex-1 min-h-[160px] max-h-[220px] overflow-y-auto bg-black/70 rounded-lg p-3 border border-slate-800 space-y-1.5 text-xs select-text">
        {displayTask && displayTask.logs && displayTask.logs.length > 0 ? (
          displayTask.logs.map((log, idx) => (
            <div key={idx} className="flex items-start gap-2 leading-relaxed">
              <span className="text-slate-500 text-[10px] whitespace-nowrap">
                [{log.formatted_time}]
              </span>
              <span
                className={`text-[9px] font-bold px-1 py-0.2 rounded border uppercase whitespace-nowrap ${getLogBadge(
                  log.level
                )}`}
              >
                {log.level}
              </span>
              <span className="text-slate-300 text-[11px] break-all">{log.message}</span>
            </div>
          ))
        ) : (
          <div className="text-slate-600 text-xs italic">
            Console idle. Telemetry streaming at 10Hz...
          </div>
        )}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
};
