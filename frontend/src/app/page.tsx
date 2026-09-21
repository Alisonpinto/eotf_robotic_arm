'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Bot,
  Camera,
  CheckCircle2,
  Crosshair,
  Eye,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { matchCommand } from '@/lib/api';
import { CommandMatchResponse, MatchedTarget, StructuredTask } from '@/types';
import { VisionInspector } from '@/components/VisionInspector';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  understanding?: string;
  searchingText?: string;
  foundText?: string;
  target?: MatchedTarget | null;
  candidates?: MatchedTarget[];
  structuredTask?: StructuredTask | null;
  status?: 'searching' | 'found' | 'not_found' | 'ambiguous' | 'error';
  reason?: string;
  isProcessing?: boolean;
}

export default function AssistantChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isVisionOpen, setIsVisionOpen] = useState<boolean>(false);
  const [visionQuery, setVisionQuery] = useState<{ name?: string; color?: string }>({
    name: 'bottle',
    color: 'red',
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isProcessing]);

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleSend = async (textToSend?: string) => {
    const commandText = (textToSend || input).trim();
    if (!commandText || isProcessing) return;

    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const userMessageId = `user_${Date.now()}`;
    const assistantMessageId = `assistant_${Date.now()}`;

    // Add user message
    const userMsg: Message = {
      id: userMessageId,
      role: 'user',
      content: commandText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    // Create preliminary assistant message in "searching" state
    const initialAssistantMsg: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      status: 'searching',
      isProcessing: true,
    };
    setMessages((prev) => [...prev, initialAssistantMsg]);

    try {
      // Step 1: Send to Natural Language Command -> Object Matching pipeline
      const res: CommandMatchResponse = await matchCommand(commandText);

      const targetObj = res.task.object;
      const targetColor = targetObj?.color || targetObj?.attributes?.color || '';
      const targetName = targetObj?.name || 'object';
      const targetDesc = `${targetColor ? targetColor + ' ' : ''}${targetName}`.trim();

      // Configure vision query for modal inspection
      setVisionQuery({
        name: targetName,
        color: targetColor || undefined,
      });

      // Update message with understanding and search progress
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                understanding: res.understanding,
                searchingText: `Looking for the ${targetDesc}...`,
                isProcessing: true,
                structuredTask: res.task,
              }
            : msg
        )
      );

      // Brief pause for realistic perception feedback
      await new Promise((resolve) => setTimeout(resolve, 550));

      // Update message with detection outcome
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== assistantMessageId) return msg;

          if (res.found && res.target && !res.ambiguous) {
            return {
              ...msg,
              status: 'found',
              foundText: `I found the ${targetDesc}.`,
              target: res.target,
              candidates: res.candidates,
              isProcessing: false,
            };
          } else if (res.ambiguous && res.candidates.length > 0) {
            return {
              ...msg,
              status: 'ambiguous',
              foundText: `I found ${res.candidates.length} candidate ${targetName}s in the camera feed. Which one would you like me to select?`,
              candidates: res.candidates,
              target: res.target,
              isProcessing: false,
            };
          } else {
            return {
              ...msg,
              status: 'not_found',
              foundText: `I looked for the ${targetDesc}, but could not find it in the camera feed.`,
              reason: res.reason,
              isProcessing: false,
            };
          }
        })
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                status: 'error',
                content: "I couldn't process that command. Please ensure the vision pipeline is connected.",
                isProcessing: false,
              }
            : msg
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const samplePrompts = [
    'Robot 1 pick the red bottle and give it to Robot 2',
    'Robot 1 pick the mango and give it to Robot 2',
    'Robot 1 pick the mobile phone and give it to Robot 2',
    'Robot 1 pick the blue cup and give it to Robot 2',
  ];

  const handleInspectTarget = (task?: StructuredTask | null) => {
    if (task?.object) {
      setVisionQuery({
        name: task.object.name,
        color: task.object.color || task.object.attributes.color || undefined,
      });
    }
    setIsVisionOpen(true);
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#18181b] text-zinc-100 selection:bg-zinc-700 selection:text-white">
      {/* Minimal Top Navigation Header */}
      <header className="sticky top-0 z-20 w-full border-b border-zinc-800/80 bg-[#18181b]/80 backdrop-blur-md">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-zinc-800 border border-zinc-700/60 flex items-center justify-center text-zinc-300">
              <Bot className="w-4 h-4" />
            </div>
            <span className="font-semibold text-sm tracking-tight text-zinc-200">
              Robot AI
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setIsVisionOpen(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium text-zinc-300 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 hover:border-zinc-600 transition-colors"
              title="Open Live Camera Feed & YOLO Vision Detector"
            >
              <Camera className="w-3.5 h-3.5 text-cyan-400" />
              <span>Camera Stream</span>
            </button>

            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium text-zinc-400 bg-zinc-900 border border-zinc-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Connected
            </span>
          </div>
        </div>
      </header>

      {/* Main Minimal Chat Area */}
      <main className="flex-1 flex flex-col justify-between max-w-3xl mx-auto w-full px-4 sm:px-6">
        {messages.length === 0 ? (
          /* Initial Clean Welcome View */
          <div className="flex-1 flex flex-col items-center justify-center text-center my-auto py-16">
            <div className="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-6 shadow-xl">
              <Bot className="w-7 h-7 text-zinc-200" />
            </div>

            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-zinc-100 mb-2">
              Robot AI
            </h1>
            <p className="text-base text-zinc-400 mb-10 max-w-md">
              Type natural-language commands to detect and target objects in real time.
            </p>

            <div className="flex flex-col sm:flex-row flex-wrap gap-2.5 justify-center max-w-lg">
              {samplePrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt)}
                  className="px-4 py-2.5 text-xs sm:text-sm text-zinc-300 bg-zinc-900/90 hover:bg-zinc-800/90 border border-zinc-800/80 hover:border-zinc-700 rounded-xl transition-all text-left"
                >
                  &ldquo;{prompt}&rdquo;
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Active Chat Thread */
          <div className="flex-1 py-8 space-y-6">
            {messages.map((msg) => (
              <div key={msg.id} className="space-y-4">
                {msg.role === 'user' ? (
                  /* User Bubble */
                  <div className="flex justify-end">
                    <div className="max-w-[85%] sm:max-w-[75%] rounded-3xl bg-[#27272a] text-zinc-100 px-5 py-3 text-sm sm:text-base leading-relaxed break-words shadow-sm">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  /* Assistant Flow */
                  <div className="flex items-start gap-3.5 max-w-[95%] sm:max-w-[88%]">
                    <div className="w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700/60 flex items-center justify-center text-zinc-300 shrink-0 mt-1">
                      <Bot className="w-4 h-4" />
                    </div>

                    <div className="flex-1 space-y-3">
                      {/* Step 1: Conversational Intent Understanding */}
                      {msg.understanding && (
                        <p className="text-sm sm:text-base text-zinc-100 leading-relaxed font-normal">
                          {msg.understanding}
                        </p>
                      )}

                      {/* Step 1.5: Interpreted Instruction Structure (Step 1 Transfer Schema) */}
                      {msg.structuredTask && (
                        <div className="p-3.5 rounded-xl bg-zinc-900 border border-zinc-800 font-mono text-xs max-w-md shadow-md space-y-2">
                          <div className="flex items-center justify-between pb-1.5 border-b border-zinc-800/80 text-zinc-400">
                            <span className="flex items-center gap-1.5 text-cyan-400 font-semibold text-[11px] tracking-wider uppercase">
                              <Sparkles className="w-3.5 h-3.5" /> Interpreted Instruction
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-sans">
                              Dual Fixed 6-DOF Arms
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 pt-1 text-zinc-200">
                            <div>
                              <span className="text-zinc-500 block text-[10px] uppercase tracking-wider">Action:</span>
                              <strong className="text-zinc-100 font-semibold uppercase">{msg.structuredTask.action}</strong>
                            </div>
                            <div>
                              <span className="text-zinc-500 block text-[10px] uppercase tracking-wider">Object:</span>
                              <strong className="text-emerald-400 font-semibold capitalize">
                                {msg.structuredTask.object_name || msg.structuredTask.object?.name || 'Unspecified'}
                              </strong>
                            </div>
                            <div>
                              <span className="text-zinc-500 block text-[10px] uppercase tracking-wider">Colour:</span>
                              <span className={msg.structuredTask.colour || msg.structuredTask.object?.colour || msg.structuredTask.color ? "text-cyan-300 capitalize font-medium" : "text-zinc-500 italic"}>
                                {msg.structuredTask.colour || msg.structuredTask.object?.colour || msg.structuredTask.color || 'null (unspecified)'}
                              </span>
                            </div>
                            <div>
                              <span className="text-zinc-500 block text-[10px] uppercase tracking-wider">Source Robot:</span>
                              <span className="text-zinc-100 font-medium">
                                {msg.structuredTask.source_robot || msg.structuredTask.source || 'Robot 1'}
                              </span>
                            </div>
                            <div className="col-span-2">
                              <span className="text-zinc-500 block text-[10px] uppercase tracking-wider">Destination Robot:</span>
                              <span className="text-zinc-100 font-medium">
                                {msg.structuredTask.destination_robot || msg.structuredTask.destination || 'Robot 2'}
                              </span>
                            </div>
                          </div>

                          <div className="pt-2 border-t border-zinc-800/60 flex items-center gap-1.5 text-[10px] text-zinc-500">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                            <span>Fixed-base requirement: Only arm joints & grippers move. Base is completely fixed.</span>
                          </div>
                        </div>
                      )}

                      {/* Step 2: "Looking for the..." State */}
                      {msg.searchingText && (
                        <div className="flex items-center gap-2 text-xs sm:text-sm text-zinc-400 font-normal">
                          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                          <span>{msg.searchingText}</span>
                        </div>
                      )}

                      {/* Step 3: Detection Outcome */}
                      {msg.foundText && (
                        <div className="pt-1">
                          <p className="text-sm sm:text-base text-zinc-100 font-medium">
                            {msg.foundText}
                          </p>
                        </div>
                      )}

                      {/* Step 4: Structured Target Information Card */}
                      {msg.status === 'found' && msg.target && (
                        <div className="mt-2 p-4 rounded-xl bg-zinc-900 border border-zinc-800/80 font-mono text-xs max-w-md shadow-lg space-y-2.5">
                          <div className="flex items-center justify-between pb-2 border-b border-zinc-800 text-zinc-400">
                            <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px] tracking-wider uppercase">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Target Validated
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800 text-cyan-300 font-sans font-medium">
                              Table Coordinates Active
                            </span>
                          </div>

                          <div className="space-y-1.5 pt-0.5 text-zinc-200">
                            {/* Object Name & Colour */}
                            <div className="flex items-center justify-between">
                              <span className="text-zinc-400">Object Name:</span>
                              <strong className="text-emerald-400 capitalize font-bold">
                                {msg.target.name}
                              </strong>
                            </div>

                            <div className="flex items-center justify-between">
                              <span className="text-zinc-400">Colour:</span>
                              <span className={msg.target.color ? "text-cyan-300 font-semibold capitalize" : "text-zinc-500 italic"}>
                                {msg.target.color || 'null (unspecified)'}
                              </span>
                            </div>

                            <div className="flex items-center justify-between">
                              <span className="text-zinc-400">Detection Confidence:</span>
                              <span className="text-cyan-400 font-bold">
                                {Math.round(msg.target.confidence * 100)}%
                              </span>
                            </div>

                            {/* Pixel Coordinates: IMAGE_COORDINATES_PIXELS */}
                            <div className="flex items-center justify-between pt-1.5 border-t border-zinc-800/60">
                              <span className="text-zinc-400 flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                                Pixel X / Y:
                              </span>
                              <span className="text-zinc-100 font-medium">
                                X: {msg.target.center.x} px, Y: {msg.target.center.y} px
                              </span>
                            </div>

                            {/* Table Coordinates: TABLE_COORDINATES */}
                            {msg.target.table_coordinates && (
                              <div className="flex items-center justify-between bg-zinc-950/80 p-2 rounded-lg border border-amber-500/20">
                                <span className="text-amber-400 font-semibold flex items-center gap-1.5 text-[11px]">
                                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                                  Table X / Y / Z:
                                </span>
                                <span className="text-amber-200 font-bold text-xs">
                                  X: {msg.target.table_coordinates.x} mm, Y: {msg.target.table_coordinates.y} mm, Z: {msg.target.table_coordinates.z} mm
                                </span>
                              </div>
                            )}

                            {/* Dimensions */}
                            <div className="flex items-center justify-between text-[11px] text-zinc-300">
                              <span className="text-zinc-400">Dimensions:</span>
                              <span>
                                {msg.target.bounding_box.x2 - msg.target.bounding_box.x1} x {msg.target.bounding_box.y2 - msg.target.bounding_box.y1} px
                                {msg.target.table_dimensions && (
                                  <span className="text-amber-300 ml-1 font-medium">
                                    (~{msg.target.table_dimensions.width_mm} x {msg.target.table_dimensions.length_mm} mm)
                                  </span>
                                )}
                              </span>
                            </div>
                          </div>

                          <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[10px] text-zinc-500">
                            <span>Frame: TABLE_COORDINATES (Placeholder)</span>
                            <button
                              onClick={() => handleInspectTarget(msg.structuredTask)}
                              className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 font-sans font-medium transition-colors"
                            >
                              <Eye className="w-3 h-3" />
                              Inspect on Camera
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Step 4 (Ambiguous): Multiple Candidates List */}
                      {msg.status === 'ambiguous' && msg.candidates && (
                        <div className="mt-2 space-y-2 max-w-md">
                          {msg.candidates.map((cand, cIdx) => (
                            <div
                              key={cIdx}
                              className="p-3 rounded-xl bg-zinc-900 border border-zinc-800 font-mono text-xs space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-zinc-200 capitalize">
                                  Candidate {cIdx + 1}: {cand.color ? `${cand.color} ` : ''}{cand.name}
                                </span>
                                <span className="text-cyan-400 font-bold text-xs">
                                  {Math.round(cand.confidence * 100)}%
                                </span>
                              </div>
                              <div className="flex items-center justify-between text-[11px] text-zinc-400">
                                <span>Pixel: ({cand.center.x}, {cand.center.y}) px</span>
                                {cand.table_coordinates && (
                                  <span className="text-amber-300 font-medium">
                                    Table: ({cand.table_coordinates.x}, {cand.table_coordinates.y}, {cand.table_coordinates.z}) mm
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Step 4 (Not Found): Clear Explanation */}
                      {msg.status === 'not_found' && msg.reason && (
                        <div className="mt-1 p-3 rounded-xl bg-zinc-900/60 border border-zinc-800/80 text-xs font-mono text-zinc-400">
                          <span>{msg.reason}</span>
                        </div>
                      )}

                      {/* Fallback plain content if provided */}
                      {msg.content && !msg.understanding && (
                        <p className="text-sm sm:text-base text-zinc-100 leading-relaxed">
                          {msg.content}
                        </p>
                      )}

                      {/* Typing indicator */}
                      {msg.isProcessing && (
                        <div className="flex items-center gap-1.5 pt-1 text-zinc-500">
                          <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-pulse" />
                          <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-pulse delay-150" />
                          <span className="w-1.5 h-1.5 rounded-full bg-zinc-400 animate-pulse delay-300" />
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Minimal Sticky Prompt Bar */}
        <div className="sticky bottom-0 z-10 w-full pt-2 pb-6 bg-gradient-to-t from-[#18181b] via-[#18181b] to-transparent">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="relative flex items-end rounded-3xl bg-[#27272a] border border-zinc-700/70 focus-within:border-zinc-500 transition-all shadow-xl px-4 py-2"
          >
            <button
              type="button"
              onClick={() => setIsVisionOpen(true)}
              className="mb-1 p-2 rounded-full text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/80 transition-colors mr-1"
              title="Open Live Camera Feed & YOLO Vision Subsystem"
            >
              <Camera className="w-4 h-4" />
            </button>

            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask the robot to do something (e.g. Pick the red bottle)..."
              disabled={isProcessing}
              className="flex-1 max-h-[180px] bg-transparent resize-none outline-none text-zinc-100 placeholder-zinc-500 text-sm sm:text-base py-2 pr-3 leading-relaxed"
            />

            <button
              type="submit"
              disabled={!input.trim() || isProcessing}
              className={`mb-1 p-2 rounded-full transition-all flex items-center justify-center shrink-0 ${
                input.trim() && !isProcessing
                  ? 'bg-zinc-100 hover:bg-white text-zinc-900 shadow-md active:scale-95'
                  : 'bg-zinc-700/50 text-zinc-500 cursor-not-allowed'
              }`}
              title="Send instruction"
            >
              <ArrowUp className="w-4 h-4 stroke-[2.5]" />
            </button>
          </form>

          <p className="text-center text-[11px] text-zinc-500 mt-2 font-normal">
            Robot AI detects objects and extracts camera coordinates for motion planning.
          </p>
        </div>
      </main>

      {/* Vision Inspector Modal (Live Webcam + Target Locked Overlay) */}
      <VisionInspector
        isOpen={isVisionOpen}
        onClose={() => setIsVisionOpen(false)}
        initialQuery={visionQuery}
      />
    </div>
  );
}
