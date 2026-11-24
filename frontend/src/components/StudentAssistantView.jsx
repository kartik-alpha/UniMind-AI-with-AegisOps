import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Bot,
  User,
  BookOpen,
  AlertCircle,
  ShieldCheck,
  Zap,
  Bookmark,
  RotateCcw,
  Sparkles,
  Layers,
  CheckCircle2,
} from 'lucide-react';
import { apiFetch, getTenantId, getAuthToken, parseApiError } from '../apiClient';

export default function StudentAssistantView({ initialPrompt = '' }) {
  const [messages, setMessages] = useState([
    {
      sender: 'assistant',
      content:
        'Hello! I am UniMind AI, your official University Support Assistant. Ask me anything about attendance rules, exam grading policies, hostel guidelines, or academic deadlines.\n\nAll answers are strictly verified against official university policy documents with zero hallucination.',
      sources: [],
      grounded: true,
      groundedness_score: 1.0,
      retrieval_mode: 'hybrid',
      isStreaming: false,
    },
  ]);
  const [input, setInput] = useState(initialPrompt || '');
  const [loading, setLoading] = useState(false);
  const [retrievalMode, setRetrievalMode] = useState('hybrid');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [streamActive, setStreamActive] = useState(false);
  const [activeTenant, setActiveTenant] = useState(getTenantId());
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (initialPrompt) {
      setInput(initialPrompt);
    }
  }, [initialPrompt]);

  useEffect(() => {
    const handleTenantChange = (e) => {
      setActiveTenant(e.detail?.tenantId || getTenantId());
    };
    window.addEventListener('unimind:tenant_change', handleTenantChange);
    return () => window.removeEventListener('unimind:tenant_change', handleTenantChange);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamActive]);

  const handleSend = async (e, directText) => {
    if (e) e.preventDefault();
    const userText = (directText || input).trim();
    if (!userText || loading) return;

    setInput('');
    // Append user message
    setMessages((prev) => [
      ...prev,
      { sender: 'user', content: userText, timestamp: new Date().toLocaleTimeString() },
    ]);
    setLoading(true);

    // Placeholder for incoming assistant stream
    const assistantIndex = messages.length + 1;
    let accumulatedContent = '';

    setMessages((prev) => [
      ...prev,
      {
        sender: 'assistant',
        content: '',
        sources: [],
        grounded: true,
        groundedness_score: null,
        retrieval_mode: retrievalMode,
        isStreaming: true,
        isError: false,
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);

    setStreamActive(true);

    try {
      const token = getAuthToken();
      const streamRes = await fetch('/api/v1/assistant/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': getTenantId(),
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: userText,
          mode: retrievalMode,
          category_filter: categoryFilter || null,
        }),
      });

      if (!streamRes.ok) {
        // Fallback or parse error
        const prob = await parseApiError(streamRes);
        throw new Error(prob.detail || `Server returned HTTP ${streamRes.status}`);
      }

      // Read SSE stream
      const reader = streamRes.body?.getReader();
      if (!reader) {
        throw new Error('Streaming response body is not readable.');
      }

      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let streamFinished = false;

      while (!streamFinished) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const jsonPayload = trimmed.slice(5).trim();
          if (!jsonPayload) continue;

          try {
            const data = JSON.parse(jsonPayload);

            if (data.done) {
              streamFinished = true;
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.sender === 'assistant') {
                  next[next.length - 1] = {
                    ...last,
                    content: data.bot_answer || accumulatedContent,
                    sources: data.sources || [],
                    grounded: data.grounded ?? true,
                    groundedness_score: data.groundedness_score ?? 1.0,
                    retrieval_mode: data.retrieval_mode || retrievalMode,
                    isStreaming: false,
                    isError: false,
                  };
                }
                return next;
              });
            } else if (data.token) {
              accumulatedContent += data.token;
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last && last.sender === 'assistant') {
                  next[next.length - 1] = {
                    ...last,
                    content: accumulatedContent,
                    isStreaming: true,
                  };
                }
                return next;
              });
            }
          } catch (parseErr) {
            // Non-fatal parse warning for malformed intermediate chunk
            console.debug('SSE chunk parse issue', parseErr);
          }
        }
      }
    } catch (streamErr) {
      console.warn('SSE Streaming failed, falling back to unary /chat endpoint:', streamErr);

      // Graceful fallback to unary endpoint
      try {
        const unaryRes = await apiFetch('/api/v1/assistant/chat', {
          method: 'POST',
          body: JSON.stringify({
            message: userText,
            mode: retrievalMode,
            category_filter: categoryFilter || null,
          }),
        });

        if (unaryRes.ok) {
          const data = await unaryRes.json();
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              sender: 'assistant',
              content: data.bot_answer,
              sources: data.sources || [],
              grounded: data.grounded,
              groundedness_score: data.groundedness_score,
              retrieval_mode: data.retrieval_mode || retrievalMode,
              isStreaming: false,
              isError: false,
              timestamp: new Date().toLocaleTimeString(),
            };
            return next;
          });
        } else {
          const prob = await parseApiError(unaryRes);
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              sender: 'assistant',
              content: `Error (${prob.status}): ${prob.detail}`,
              sources: [],
              grounded: false,
              groundedness_score: 0.0,
              isStreaming: false,
              isError: true,
              timestamp: new Date().toLocaleTimeString(),
            };
            return next;
          });
        }
      } catch (fallbackErr) {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            sender: 'assistant',
            content: `Network Connection Error: Unable to communicate with UniMind AI Assistant. (${streamErr.message})`,
            sources: [],
            grounded: false,
            groundedness_score: 0.0,
            isStreaming: false,
            isError: true,
            timestamp: new Date().toLocaleTimeString(),
          };
          return next;
        });
      }
    } finally {
      setLoading(false);
      setStreamActive(false);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        sender: 'assistant',
        content:
          'Conversation reset. I am UniMind AI, your official University Support Assistant. Ask me anything about attendance rules, exam grading policies, hostel guidelines, or academic deadlines.',
        sources: [],
        grounded: true,
        groundedness_score: 1.0,
        retrieval_mode: 'hybrid',
        isStreaming: false,
      },
    ]);
  };

  const quickPrompts = [
    'What is the minimum attendance required for final exams?',
    'What is the mandatory hostel curfew time?',
    'How does grade re-evaluation work?',
    'What are the campus Wi-Fi and IT Lab guidelines?',
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">UNIMIND AI</span>
            <span className="text-[10px] bg-cyan-500/10 text-cyan-400 font-mono font-bold px-2 py-0.5 rounded border border-cyan-500/20">
              TENANT #{activeTenant}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Student AI Assistant</h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time SSE token streaming grounded against verified institutional policy documents.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          {/* Retrieval Mode Selector */}
          <div className="inline-flex rounded-lg border border-slate-700/60 bg-slate-800/80 p-1 shadow-sm">
            <button
              onClick={() => setRetrievalMode('hybrid')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                retrievalMode === 'hybrid'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Zap className="h-3 w-3" /> Hybrid RAG
            </button>
            <button
              onClick={() => setRetrievalMode('dense')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${
                retrievalMode === 'dense'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Dense Vector
            </button>
            <button
              onClick={() => setRetrievalMode('bm25')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${
                retrievalMode === 'bm25'
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              BM25 Lexical
            </button>
          </div>

          {/* Reset Conversation */}
          <button
            onClick={handleReset}
            title="Reset conversation"
            className="p-2 bg-slate-800 hover:bg-slate-700/80 text-slate-400 hover:text-slate-200 rounded-lg border border-slate-700 transition-colors shadow-sm"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Main Chat Canvas */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl h-[600px] flex flex-col shadow-sm">
        {/* Messages Stream */}
        <div className="flex-1 p-6 overflow-y-auto space-y-5">
          {messages.map((msg, idx) => {
            const isUser = msg.sender === 'user';
            const groundedPct =
              msg.groundedness_score !== null && msg.groundedness_score !== undefined
                ? Math.round(msg.groundedness_score * 100)
                : null;

            return (
              <div key={idx} className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
                {!isUser && (
                  <div className="h-8 w-8 rounded-lg bg-cyan-600 text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
                    <Bot className="h-5 w-5" />
                  </div>
                )}

                <div
                  className={`max-w-[82%] rounded-xl p-4 text-xs leading-relaxed ${
                    isUser
                      ? 'bg-cyan-600 text-white font-medium shadow-sm'
                      : msg.isError
                      ? 'bg-rose-950/40 text-rose-200 border border-rose-800/60 shadow-sm'
                      : 'bg-slate-900/80 text-slate-200 border border-slate-700/60'
                  }`}
                >
                  {/* Status header for assistant messages */}
                  {!isUser && msg.isError && (
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-rose-400 pb-2 mb-2 border-b border-rose-800/50">
                      <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
                      Assistant Service Error
                    </div>
                  )}

                  {!isUser && !msg.isError && msg.grounded && (
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-700/60 gap-4">
                      <span className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-400">
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                        Official University Knowledge Grounded
                      </span>
                      {groundedPct !== null && (
                        <span className="bg-emerald-500/10 text-emerald-400 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border border-emerald-500/20 shrink-0">
                          {groundedPct}% Confidence
                        </span>
                      )}
                    </div>
                  )}

                  {!isUser && !msg.isError && !msg.grounded && (
                    <div className="flex items-center gap-1 text-[11px] font-bold text-amber-400 pb-2 mb-2 border-b border-slate-700/60">
                      <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                      Zero Hallucination Guardrail Active
                    </div>
                  )}

                  {/* Message Content with Streaming Cursor */}
                  <div className="whitespace-pre-wrap font-sans">
                    {msg.content}
                    {msg.isStreaming && (
                      <span className="inline-block w-1.5 h-3.5 bg-cyan-400 ml-1 translate-y-0.5 animate-pulse" />
                    )}
                  </div>

                  {/* Citations & Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-700/60 space-y-1.5">
                      <span className="font-bold text-[11px] text-slate-300 flex items-center gap-1">
                        <BookOpen className="h-3.5 w-3.5 text-cyan-400" /> Official Sources & Citations:
                      </span>
                      {msg.sources.map((src, sIdx) => (
                        <div
                          key={sIdx}
                          className="bg-slate-800/80 rounded-lg p-2.5 border border-slate-700/60 text-[11px] text-slate-300 flex flex-col gap-1"
                        >
                          <div className="flex justify-between items-center gap-2">
                            <span className="font-bold text-slate-100 truncate">{src.title}</span>
                            {src.similarity_score !== undefined && (
                              <span className="font-mono text-emerald-400 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 shrink-0 text-[10px]">
                                {Math.round(src.similarity_score * 100)}% match
                              </span>
                            )}
                          </div>
                          {src.section_heading && (
                            <div className="text-[10px] text-cyan-300 font-medium flex items-center gap-1">
                              <Bookmark className="h-2.5 w-2.5 text-cyan-400 shrink-0" />
                              Section: {src.section_heading}
                            </div>
                          )}
                          {src.content_snippet && (
                            <p className="text-[10px] text-slate-400 italic line-clamp-2 mt-0.5">
                              "{src.content_snippet}"
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="h-8 w-8 rounded-lg bg-slate-700 text-white flex items-center justify-center shrink-0 font-bold text-xs shadow-sm mt-0.5">
                    KL
                  </div>
                )}
              </div>
            );
          })}

          {loading && !streamActive && (
            <div className="flex gap-3">
              <div className="h-8 w-8 rounded-lg bg-cyan-600 text-white flex items-center justify-center">
                <Bot className="h-5 w-5 animate-spin" />
              </div>
              <div className="bg-slate-800/60 rounded-xl p-3 text-xs text-slate-400 border border-slate-700/50 animate-pulse">
                Querying hybrid dense-lexical index and enforcing ground truth policies...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Queries Suggestions Bar */}
        <div className="px-4 py-2 bg-slate-900/60 border-t border-slate-700/60 flex items-center gap-2 overflow-x-auto">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider shrink-0">
            Suggested Queries:
          </span>
          {quickPrompts.map((p, idx) => (
            <button
              key={idx}
              onClick={(e) => handleSend(e, p)}
              disabled={loading}
              className="bg-slate-800 hover:bg-cyan-500/10 hover:text-cyan-300 hover:border-cyan-500/30 text-slate-300 text-[10px] px-2.5 py-1 rounded-md transition-colors font-medium border border-slate-700/60 shrink-0 disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>

        {/* User Input Bar */}
        <form
          onSubmit={handleSend}
          className="p-4 border-t border-slate-700/60 bg-slate-900/80 rounded-b-xl flex gap-3"
        >
          <input
            type="text"
            placeholder="Ask a question about university attendance, exams, hostel curfew, or academic rules..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1 bg-slate-800 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-cyan-600 hover:bg-cyan-500 text-white px-4 py-2.5 rounded-lg font-semibold text-xs flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
