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
    'Pick the red bottle.',
    'Find the blue cup.',
    'Pick the mouse.',
    'Take the green bottle and give it to the JetArm.',
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
                        <div className="mt-2 p-4 rounded-xl bg-zinc-900 border border-zinc-800/80 font-mono text-xs max-w-md shadow-lg space-y-2">
                          <div className="flex items-center justify-between pb-2 border-b border-zinc-800 text-zinc-400">
                            <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px] tracking-wider uppercase">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Target Validated
                            </span>
                            <span className="text-[10px] text-zinc-500">
                              Camera Image Coordinates
                            </span>
                          </div>

                          <div className="space-y-1.5 pt-1 text-zinc-200">
                            <div className="flex items-center justify-between">
                              <span className="text-zinc-400">Target:</span>
                              <strong className="text-zinc-100 capitalize">
                                {msg.target.color ? `${msg.target.color} ` : ''}{msg.target.name}
                              </strong>
                            </div>

                            <div className="flex items-center justify-between">
                              <span className="text-zinc-400">Confidence:</span>
                              <span className="text-cyan-400 font-bold">
                                {Math.round(msg.target.confidence * 100)}%
                              </span>
                            </div>

                            <div className="flex items-center justify-between">
                              <span className="text-zinc-400">Position:</span>
                              <span className="text-zinc-100 font-semibold">
                                ({msg.target.center.x}, {msg.target.center.y})
                              </span>
                            </div>
                          </div>

                          <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between">
                            <span className="text-[10px] text-zinc-500">
                              Motion planning ready
                            </span>
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
                              className="p-3 rounded-xl bg-zinc-900 border border-zinc-800 font-mono text-xs flex items-center justify-between"
                            >
                              <div>
                                <span className="font-semibold text-zinc-200 capitalize">
                                  Candidate {cIdx + 1}: {cand.color ? `${cand.color} ` : ''}{cand.name}
                                </span>
                                <span className="text-zinc-400 block text-[11px]">
                                  Position: ({cand.center.x}, {cand.center.y})
                                </span>
                              </div>
                              <span className="text-cyan-400 font-bold text-xs">
                                {Math.round(cand.confidence * 100)}%
                              </span>
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
