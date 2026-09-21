'use client';

import React, { useState } from 'react';
import {
  ArrowDown,
  Bot,
  ChevronDown,
  ChevronUp,
  CornerDownLeft,
  Loader2,
  Package,
  Sparkles,
  Target,
  Wand2,
  Zap,
} from 'lucide-react';
import { executeNaturalCommand, previewCommandPlan, parseCommand } from '@/lib/api';
import { ActionPlan, StructuredTask, TaskRecord } from '@/types';

interface CommandInputProps {
  isConnected: boolean;
  onCommandLaunched: () => void;
}

export const CommandInput: React.FC<CommandInputProps> = ({
  isConnected,
  onCommandLaunched,
}) => {
  const [command, setCommand] = useState<string>('');
  const [targetRobot, setTargetRobot] = useState<string>('auto');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastExecutedTask, setLastExecutedTask] = useState<StructuredTask | null>(null);
  const [lastExecutedPlan, setLastExecutedPlan] = useState<ActionPlan | null>(null);
  const [previewPlan, setPreviewPlan] = useState<ActionPlan | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const suggestedCommands = [
    'Pick the red bottle.',
    'Pick the blue cup and give it to the JetArm.',
    'Find the box and move it to the right.',
    'Inspect the green cylinder on the workbench.',
    'Home both robotic arms to calibration position.',
  ];

  const handleExecute = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!command.trim() || isLoading || !isConnected) return;

    setIsLoading(true);
    setError(null);

    try {
      const preferred = targetRobot === 'auto' ? undefined : targetRobot;
      const taskRecord: TaskRecord = await executeNaturalCommand(command.trim(), preferred);

      // Extract structured task from response or fallback to parser
      const structured =
        taskRecord.structured_task ||
        taskRecord.plan?.structured_task ||
        (await parseCommand(command.trim(), preferred));

      setLastExecutedTask(structured);
      setLastExecutedPlan(taskRecord.plan);
      setCommand('');
      setPreviewPlan(null);
      setIsPreviewOpen(false);
      onCommandLaunched();
    } catch (err: any) {
      setError(err.message || 'Execution request failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePreview = async () => {
    if (!command.trim() || isLoading || !isConnected) return;
    setIsLoading(true);
    setError(null);
    try {
      const preferred = targetRobot === 'auto' ? undefined : targetRobot;
      const plan = await previewCommandPlan(command.trim(), preferred);
      setPreviewPlan(plan);
      if (plan.structured_task) {
        setLastExecutedTask(plan.structured_task);
      }
      setIsPreviewOpen(true);
    } catch (err: any) {
      setError(err.message || 'Plan preview failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-indigo-500/30 bg-slate-900/70 backdrop-blur-md p-5 shadow-xl">
      {/* Title & Target Arm Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-950/80 text-indigo-400 border border-indigo-500/40 shadow-[0_0_12px_rgba(99,102,241,0.3)]">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 font-mono tracking-wide flex items-center gap-2">
              NATURAL-LANGUAGE AI COMMAND CONSOLE
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              Dynamic Semantic Parser • Arbitrary Instructions • Dual-Arm Multi-Step Dispatch
            </p>
          </div>
        </div>

        {/* Robot Target Selector */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400">Target:</span>
          <select
            value={targetRobot}
            onChange={(e) => setTargetRobot(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-2.5 py-1.5 focus:border-indigo-500 focus:outline-none transition-colors"
          >
            <option value="auto">Auto-Detect</option>
            <option value="jetarm">Hiwonder JetArm</option>
            <option value="diy_arm">DIY 3D-Printed Arm</option>
            <option value="both">Both Robotic Arms</option>
          </select>
        </div>
      </div>

      {/* Input Field & Action Buttons */}
      <form onSubmit={handleExecute} className="relative flex flex-col sm:flex-row gap-2 mb-3">
        <div className="relative flex-1">
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Type any arbitrary instruction (e.g. 'Pick the red bottle and give it to the JetArm', 'Find the box and move it to the right')..."
            disabled={!isConnected || isLoading}
            className="w-full bg-slate-950/90 border border-slate-700 focus:border-indigo-500 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 font-mono text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all disabled:opacity-50"
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Preview Plan Button */}
          <button
            type="button"
            onClick={handlePreview}
            disabled={!isConnected || isLoading || !command.trim()}
            className="inline-flex items-center gap-1.5 px-3.5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono font-medium border border-slate-700 hover:border-slate-600 transition-all disabled:opacity-40"
            title="Inspect AI plan decomposition without executing"
          >
            <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Preview</span>
          </button>

          {/* Primary Execute Button */}
          <button
            type="submit"
            disabled={!isConnected || isLoading || !command.trim()}
            className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white font-mono font-bold text-xs sm:text-sm tracking-wider shadow-lg shadow-indigo-600/30 hover:shadow-indigo-600/50 transition-all active:scale-95 disabled:opacity-40"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>PARSING...</span>
              </>
            ) : (
              <>
                <span>EXECUTE</span>
                <CornerDownLeft className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Error notification */}
      {error && (
        <div className="mb-3 px-3 py-2 rounded-lg bg-rose-950/70 border border-rose-500/50 text-rose-300 font-mono text-xs">
          {error}
        </div>
      )}

      {/* Suggested Prompt Chips */}
      <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] mb-2">
        <span className="text-slate-400 flex items-center gap-1 mr-1">
          <Sparkles className="w-3 h-3 text-amber-400" /> Examples:
        </span>
        {suggestedCommands.map((chip, i) => (
          <button
            key={i}
            type="button"
            onClick={() => setCommand(chip)}
            className="px-2.5 py-1 rounded-full bg-slate-950/80 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/40 transition-colors truncate max-w-xs text-left"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* EXACT 4-STAGE INTERPRETATION PIPELINE:
          User command -> Interpreted task -> Extracted object -> Action */}
      {lastExecutedTask && (
        <div className="mt-4 rounded-xl border border-cyan-500/40 bg-slate-950/90 p-4 font-mono shadow-2xl transition-all animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 mb-3">
            <div className="flex items-center gap-2 text-xs font-bold text-cyan-400">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>COMMAND INTERPRETATION PIPELINE</span>
            </div>
            <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-700/50 font-semibold">
              {Math.round(lastExecutedTask.confidence * 100)}% Confidence
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {/* Stage 1: User command */}
            <div className="rounded-lg bg-slate-900/90 border border-slate-800/90 p-2.5">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold mb-1 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                User command
              </div>
              <div className="text-xs sm:text-sm font-semibold text-slate-100 italic">
                &ldquo;{lastExecutedTask.raw_command}&rdquo;
              </div>
            </div>

            {/* Down Arrow 1 */}
            <div className="flex justify-center text-cyan-400 -my-0.5">
              <ArrowDown className="w-3.5 h-3.5 animate-bounce" />
            </div>

            {/* Stage 2: Interpreted task */}
            <div className="rounded-lg bg-slate-900/90 border border-sky-500/30 p-2.5">
              <div className="text-[10px] uppercase tracking-wider text-sky-400 font-bold mb-1 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                Interpreted task
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="font-bold text-sky-300 text-sm">
                  {lastExecutedTask.action}
                </span>
                {lastExecutedTask.source && (
                  <span className="px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-700 text-[11px]">
                    Source: <strong className="text-cyan-400">{lastExecutedTask.source}</strong>
                  </span>
                )}
                {lastExecutedTask.destination && (
                  <span className="px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-700 text-[11px]">
                    Destination: <strong className="text-amber-400">{lastExecutedTask.destination}</strong>
                  </span>
                )}
              </div>
              {lastExecutedTask.summary && (
                <div className="text-[11px] text-slate-400 mt-1.5">
                  {lastExecutedTask.summary}
                </div>
              )}
            </div>

            {/* Down Arrow 2 */}
            <div className="flex justify-center text-indigo-400 -my-0.5">
              <ArrowDown className="w-3.5 h-3.5 animate-bounce" />
            </div>

            {/* Stage 3: Extracted object */}
            <div className="rounded-lg bg-slate-900/90 border border-indigo-500/30 p-2.5">
              <div className="text-[10px] uppercase tracking-wider text-indigo-400 font-bold mb-1 flex items-center gap-1.5">
                <Package className="w-3 h-3 text-indigo-400" />
                Extracted object
              </div>
              {lastExecutedTask.object ? (
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-bold text-indigo-300 text-sm capitalize">
                    {lastExecutedTask.object.name}
                  </span>
                  {lastExecutedTask.object.attributes.color && (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-700 text-[11px]">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          lastExecutedTask.object.attributes.color === 'red'
                            ? 'bg-rose-500'
                            : lastExecutedTask.object.attributes.color === 'blue'
                            ? 'bg-sky-500'
                            : lastExecutedTask.object.attributes.color === 'green'
                            ? 'bg-emerald-500'
                            : lastExecutedTask.object.attributes.color === 'yellow'
                            ? 'bg-amber-400'
                            : 'bg-slate-400'
                        }`}
                      />
                      Color: <strong className="text-white capitalize">{lastExecutedTask.object.attributes.color}</strong>
                    </span>
                  )}
                  {lastExecutedTask.object.attributes.size && (
                    <span className="px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-700 text-[11px]">
                      Size: <strong className="text-white">{lastExecutedTask.object.attributes.size}</strong>
                    </span>
                  )}
                  {lastExecutedTask.object.attributes.shape && (
                    <span className="px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-700 text-[11px]">
                      Shape: <strong className="text-white">{lastExecutedTask.object.attributes.shape}</strong>
                    </span>
                  )}
                  {lastExecutedTask.object.quantity && (
                    <span className="px-2 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-700 text-[11px]">
                      Qty: <strong className="text-white">{lastExecutedTask.object.quantity}</strong>
                    </span>
                  )}
                </div>
              ) : (
                <div className="text-xs text-slate-500 italic">
                  No discrete physical object entity (Kinematic / spatial instruction)
                </div>
              )}
            </div>

            {/* Down Arrow 3 */}
            <div className="flex justify-center text-emerald-400 -my-0.5">
              <ArrowDown className="w-3.5 h-3.5 animate-bounce" />
            </div>

            {/* Stage 4: Action */}
            <div className="rounded-lg bg-slate-900/90 border border-emerald-500/30 p-2.5">
              <div className="text-[10px] uppercase tracking-wider text-emerald-400 font-bold mb-1 flex items-center gap-1.5">
                <Zap className="w-3 h-3 text-emerald-400" />
                Action
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-600/50 font-bold uppercase tracking-wider text-xs">
                    {lastExecutedTask.action}
                  </span>
                  <span className="text-slate-300 text-xs">
                    Active in task manager ({lastExecutedPlan?.actions.length ?? 'multi'}-step plan)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Plan Details Toggle */}
      {previewPlan && (
        <div className="mt-4 pt-4 border-t border-slate-800 font-mono text-xs">
          <div
            onClick={() => setIsPreviewOpen(!isPreviewOpen)}
            className="flex items-center justify-between cursor-pointer text-indigo-400 font-semibold mb-2"
          >
            <span className="flex items-center gap-1.5">
              <Bot className="w-4 h-4" /> Decomposed Step Trajectory ({previewPlan.actions.length} steps)
            </span>
            {isPreviewOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>

          {isPreviewOpen && (
            <div className="bg-slate-950/90 rounded-lg p-3 border border-slate-800 space-y-1.5">
              {previewPlan.actions.map((step, idx) => (
                <div
                  key={step.action_id}
                  className="flex items-center gap-2 text-[11px] bg-slate-900/80 rounded px-2 py-1 border border-slate-800"
                >
                  <span className="text-indigo-400 font-bold">#{idx + 1}</span>
                  <span className="px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-700/40 font-mono text-[10px]">
                    {step.action_type}
                  </span>
                  <span className="text-slate-300 flex-1">{step.description}</span>
                  <span className="text-slate-500 font-mono text-[10px]">{step.robot_id}</span>
                </div>
              ))}

              <div className="mt-3 flex justify-end">
                <button
                  onClick={handleExecute}
                  disabled={isLoading}
                  className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-bold text-xs"
                >
                  Confirm & Dispatch
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
