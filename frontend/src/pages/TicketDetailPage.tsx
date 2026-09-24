import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  RotateCw,
  Send,
  Edit3,
  UserX,
  CheckCircle2,
  Database,
  ExternalLink,
  Cpu,
  Clock,
  MessageCircle,
  Repeat,
  Heart,
  Bookmark,
  Share2,
  BadgeCheck,
  Twitter,
  Trash2,
  Globe,
} from 'lucide-react';
import { api } from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';
import { InferenceResponse, Ticket } from '../types';
import { FormattedTweet } from '../components/common/FormattedTweet';
import { useSSE } from '../hooks/useSSE';
import { StreamingDraft } from '../components/StreamingDraft';

export const TicketDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { user: currentUser } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'cockpit' | 'twitter'>('cockpit');
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [inference, setInference] = useState<InferenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [inferring, setInferring] = useState(false);
  const [inferenceError, setInferenceError] = useState<string | null>(null);
  const [replyText, setReplyText] = useState('');
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [submittingAction, setSubmittingAction] = useState(false);
  const [deletingTicket, setDeletingTicket] = useState(false);

  const {
    isStreaming,
    currentStage,
    streamedTokens,
    draftComplete,
    safetyResult: sseSafetyResult,
    pipelineComplete: ssePipelineComplete,
    totalMs: sseTotalMs,
    startStream,
  } = useSSE();

  useEffect(() => {
    if (streamedTokens) {
      setReplyText(streamedTokens);
    }
  }, [streamedTokens]);

  useEffect(() => {
    if (ssePipelineComplete && id) {
      api.getTicket(id).then(setTicket).catch(console.error);
      api.runInference(id, false).then(setInference).catch(console.error);
    }
  }, [ssePipelineComplete, id]);

  const handleStartStreaming = () => {
    if (!id) return;
    setReplyText('');
    startStream(api.getStreamUrl(id));
  };

  const canDeleteTicket =
    currentUser?.email?.toLowerCase() === 'mathanprakashselvam@gmail.com' ||
    currentUser?.role === 'manager';

  const handleDeleteTicket = async () => {
    if (!id) return;
    if (!window.confirm('Are you sure you want to permanently delete this ticket? This action cannot be undone.')) {
      return;
    }
    setDeletingTicket(true);
    try {
      await api.deleteTicket(id);
      setActionSuccess('Ticket deleted successfully.');
      setTimeout(() => navigate('/inbox'), 700);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to delete ticket.');
      setDeletingTicket(false);
    }
  };

  const fetchTicketAndInference = async (refreshInference = false) => {
    if (!id) return;
    setInferenceError(null);
    try {
      if (!ticket) {
        setLoading(true);
        const ticketData = await api.getTicket(id);
        setTicket(ticketData);
        setLoading(false);
      }

      setInferring(true);
      try {
        const infData = await api.runInference(id, refreshInference);
        setInference(infData);
        setReplyText(infData.draft.reply);
      } catch (infErr: any) {
        console.error('Inference error:', infErr);
        const msg =
          infErr?.response?.data?.detail ||
          infErr?.message ||
          'Failed to connect to Ollama service. Ensure Ollama is running.';
        setInferenceError(msg);
      }
    } catch (err: any) {
      console.error('Failed to load ticket details', err);
    } finally {
      setLoading(false);
      setInferring(false);
    }
  };

  useEffect(() => {
    fetchTicketAndInference();
  }, [id]);

  const [startTime] = useState<number>(Date.now());

  const handleAction = async (action: 'approve' | 'edit' | 'reject' | 'escalate') => {
    if (!id) return;
    setSubmittingAction(true);
    const reviewTimeSec = Math.max(1, Math.round((Date.now() - startTime) / 1000));
    try {
      await api.submitFeedback(
        id,
        action,
        action === 'edit' ? replyText : undefined,
        `Action '${action}' applied by support agent.`,
        replyText,
        reviewTimeSec
      );
      if (action === 'approve' || action === 'edit') {
        setActionSuccess('Draft approved & resolution stored in Knowledge Base.');
      } else if (action === 'escalate') {
        setActionSuccess('Ticket escalated to specialist queue.');
      } else {
        setActionSuccess('Draft rejected.');
      }
      setTimeout(() => {
        navigate('/inbox');
      }, 1500);
    } catch (err) {
      console.error('Failed to submit feedback', err);
    } finally {
      setSubmittingAction(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500 dark:text-neutral-400 text-sm">
        <RotateCw className="h-5 w-5 animate-spin mr-2 text-sky-500" />
        Loading ticket...
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className="p-8 text-center text-slate-500 dark:text-neutral-400">
        Ticket not found.
      </div>
    );
  }

  const isEscalation = inference?.escalation?.decision === 'escalate';

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-slate-50 dark:bg-black text-slate-900 dark:text-neutral-100">
      {/* Top Navigation Header */}
      <header className="flex-shrink-0 bg-white dark:bg-black border-b border-slate-200 dark:border-neutral-800 px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/inbox')}
            className="p-1.5 text-slate-500 dark:text-neutral-400 hover:text-slate-800 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-neutral-900 rounded-full transition"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <div className="flex items-center space-x-2.5">
              <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
                Ticket #{ticket.id.slice(0, 8)}
              </h2>
              <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border ${
                ticket.status === 'resolved'
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                  : ticket.status === 'escalated'
                  ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
                  : 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20'
              }`}>
                {ticket.status}
              </span>
            </div>
            <p className="text-xs text-slate-400 dark:text-neutral-500">
              Customer: {ticket.tweet_author || '@customer'}
            </p>
          </div>
        </div>

        {/* View Switcher Tabs (X-Style Pill Selector) */}
        <div className="flex items-center space-x-3">
          <div className="bg-slate-100 dark:bg-neutral-900 p-1 rounded-full flex items-center space-x-1 border border-slate-200 dark:border-neutral-800">
            <button
              onClick={() => setActiveTab('cockpit')}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center space-x-1.5 ${
                activeTab === 'cockpit'
                  ? 'bg-white dark:bg-neutral-800 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Cpu className="h-3.5 w-3.5 text-sky-500" />
              <span>Agent Cockpit</span>
            </button>
            <button
              onClick={() => setActiveTab('twitter')}
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all flex items-center space-x-1.5 ${
                activeTab === 'twitter'
                  ? 'bg-white dark:bg-neutral-800 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Twitter className="h-3.5 w-3.5 text-sky-500 fill-current" />
              <span>Customer Twitter View</span>
              {ticket.status === 'resolved' && (
                <span className="w-2 h-2 rounded-full bg-emerald-500" title="Delivered on Twitter" />
              )}
            </button>
          </div>

          <button
            onClick={handleStartStreaming}
            disabled={isStreaming || inferring}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-bold text-sky-600 dark:text-sky-400 bg-sky-500/10 hover:bg-sky-500/20 rounded-full border border-sky-500/30 transition shadow-sm"
          >
            <Sparkles className={`h-3.5 w-3.5 ${isStreaming ? 'animate-spin' : ''}`} />
            <span>{isStreaming ? 'Streaming Draft...' : 'Stream Live AI'}</span>
          </button>

          <button
            onClick={() => fetchTicketAndInference(true)}
            disabled={inferring || isStreaming}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-slate-700 dark:text-neutral-300 bg-slate-100 dark:bg-neutral-900 hover:bg-slate-200 dark:hover:bg-neutral-800 rounded-full border border-slate-200 dark:border-neutral-800 transition"
          >
            <RotateCw className={`h-3.5 w-3.5 ${inferring ? 'animate-spin text-sky-500' : ''}`} />
            <span>Re-run AI</span>
          </button>

          {canDeleteTicket && (
            <button
              onClick={handleDeleteTicket}
              disabled={deletingTicket}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold text-rose-600 dark:text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 rounded-full border border-rose-500/20 transition"
              title="Permanently delete ticket"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{deletingTicket ? 'Deleting...' : 'Delete Ticket'}</span>
            </button>
          )}
        </div>
      </header>

      {/* Action Notification Banner */}
      {actionSuccess && (
        <div className="flex-shrink-0 bg-emerald-600 text-white text-xs py-2 px-6 font-bold flex items-center justify-between shadow-inner">
          <span>{actionSuccess} Redirecting to queue...</span>
        </div>
      )}

      {/* Tab 1: Agent Cockpit View */}
      {activeTab === 'cockpit' && (
        <div className="flex-1 min-h-0 p-4 lg:p-5 max-w-7xl mx-auto w-full overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-full overflow-hidden">
            {/* Left Column: Customer Context & AI Diagnostics (5 cols) */}
            <div className="lg:col-span-5 h-full overflow-y-auto pr-1 space-y-4">
              {/* Customer Message Card */}
              <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-wider">
                    Inbound Customer Tweet
                  </h3>
                  <button
                    type="button"
                    onClick={() => setActiveTab('twitter')}
                    className="text-xs font-bold text-sky-500 hover:text-sky-600 flex items-center space-x-1"
                  >
                    <span>Twitter Thread View</span>
                    <ExternalLink className="h-3 w-3" />
                  </button>
                </div>
                <div className="bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-xl p-4 text-sm font-medium text-slate-800 dark:text-neutral-200 leading-relaxed">
                  "<FormattedTweet text={ticket.customer_text} />"
                </div>
              </div>

              {/* AI Inference Status Spinner */}
              {inferring && (
                <div className="bg-sky-500/10 border border-sky-500/20 rounded-2xl p-6 text-center shadow-sm">
                  <RotateCw className="h-6 w-6 animate-spin text-sky-500 mx-auto mb-2" />
                  <p className="text-sm font-bold text-sky-600 dark:text-sky-400">Executing AI Agent Pipeline...</p>
                  <p className="text-xs text-sky-700 dark:text-sky-300/70 mt-1">Intent classification, pgvector semantic retrieval, and draft synthesis.</p>
                </div>
              )}

              {inferenceError && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5 shadow-sm">
                  <div className="flex items-center space-x-2 text-amber-600 dark:text-amber-400 font-bold mb-1">
                    <ShieldAlert className="h-5 w-5" />
                    <h3 className="text-sm">Inference Pipeline Notice</h3>
                  </div>
                  <p className="text-xs text-amber-700 dark:text-amber-300 leading-relaxed mb-3">
                    {inferenceError}
                  </p>
                  <button
                    type="button"
                    onClick={() => fetchTicketAndInference(true)}
                    className="px-3.5 py-1.5 bg-amber-500 text-white font-bold text-xs rounded-full transition shadow-sm"
                  >
                    Retry Pipeline Execution
                  </button>
                </div>
              )}

              {inference && !inferring && (
                <>
                  {/* Intent Card */}
                  <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800 p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-xs font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-wider">
                        Intent Taxonomy Classification
                      </h3>
                      <span className="text-xs font-bold text-sky-500">
                        {(inference.intent.confidence * 100).toFixed(0)}% Confidence
                      </span>
                    </div>

                    <div className="bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-xl p-3.5 mb-3 flex items-center justify-between">
                      <span className="text-sm font-bold text-slate-900 dark:text-white capitalize">
                        {inference.intent.intent.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[11px] font-mono bg-sky-500/10 text-sky-500 px-2 py-0.5 rounded-full font-bold">
                        {inference.intent.intent}
                      </span>
                    </div>

                    {inference.intent.alternatives && inference.intent.alternatives.length > 0 && (
                      <div>
                        <span className="text-[11px] font-semibold text-slate-400 dark:text-neutral-500 uppercase">Top Candidate Intents:</span>
                        <div className="mt-1.5 space-y-1">
                          {inference.intent.alternatives.map((alt, idx) => (
                            <div key={idx} className="flex items-center justify-between text-xs text-slate-600 dark:text-neutral-400">
                              <span>{alt.label.replace(/_/g, ' ')}</span>
                              <span className="text-slate-400 dark:text-neutral-500 font-mono">{(alt.confidence * 100).toFixed(0)}%</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Escalation Policy Card */}
                  <div
                    className={`rounded-2xl border p-5 shadow-sm transition-all ${
                      isEscalation
                        ? 'bg-rose-500/10 border-rose-500/30'
                        : 'bg-emerald-500/10 border-emerald-500/30'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {isEscalation ? (
                          <ShieldAlert className="h-5 w-5 text-rose-500" />
                        ) : (
                          <ShieldCheck className="h-5 w-5 text-emerald-500" />
                        )}
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                          {isEscalation ? 'Escalation Triggered' : 'Safe for Auto Resolution'}
                        </h3>
                      </div>
                      <span
                        className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                          isEscalation ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400' : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                        }`}
                      >
                        Risk: {(inference.escalation.risk_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    {isEscalation ? (
                      <div className="mt-3">
                        <span className="text-xs font-bold text-rose-600 dark:text-rose-400">Triggered Rules:</span>
                        <ul className="mt-1.5 space-y-1 text-xs text-rose-700 dark:text-rose-300 list-disc list-inside">
                          {inference.escalation.reasons.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-xs text-emerald-700 dark:text-emerald-300 mt-1">
                        All compliance policies passed. Grounded troubleshoot path identified.
                      </p>
                    )}
                  </div>

                  {/* Historical Knowledge Grounding Card */}
                  <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800 p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <Database className="h-4 w-4 text-sky-500" />
                        <h3 className="text-xs font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-wider">
                          Historical Resolutions (RAG)
                        </h3>
                      </div>
                      <span className="text-[11px] text-slate-400 dark:text-neutral-500">pgvector Top-3</span>
                    </div>

                    {!inference.retrieved || inference.retrieved.length === 0 ? (
                      <p className="text-xs text-slate-400 dark:text-neutral-500">No matching historical threads found.</p>
                    ) : (
                      <div className="space-y-3">
                        {inference.retrieved.map((thread, idx) => (
                          <div key={idx} className="bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-xl p-3.5 text-xs space-y-1.5">
                            <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-neutral-500 font-medium">
                              <span className="flex items-center space-x-1.5">
                                {thread.source === 'web_search' || thread.thread_id.startsWith('web-') ? (
                                  <span className="inline-flex items-center text-sky-500 font-bold">
                                    <Globe className="w-3 h-3 mr-1" />
                                    Apple Support Web Search
                                  </span>
                                ) : (
                                  <span>Thread #{thread.thread_id}</span>
                                )}
                              </span>
                              <span className="text-sky-500 font-bold font-mono">
                                {(thread.similarity * 100).toFixed(0)}% Match
                              </span>
                            </div>
                            <p className="text-slate-600 dark:text-neutral-400 italic">"<FormattedTweet text={thread.customer_msg} />"</p>
                            <div className="pt-1.5 border-t border-slate-200 dark:border-neutral-800 text-slate-900 dark:text-neutral-200 font-medium">
                              <span className="text-sky-500 font-bold">@AppleSupport:</span> <FormattedTweet text={thread.brand_reply} />
                            </div>
                            {thread.url && (
                              <div className="pt-1 flex items-center justify-end">
                                <a
                                  href={thread.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center space-x-1 text-[11px] text-sky-500 hover:text-sky-400 hover:underline font-semibold"
                                >
                                  <span>Official Apple Guide</span>
                                  <ExternalLink className="w-3 h-3" />
                                </a>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Right Column: AI Reply Drafter & Agent Actions (7 cols) */}
            <div className="lg:col-span-7 h-full flex flex-col justify-between overflow-hidden bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-5 shadow-sm">
              <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
                <div className="flex-shrink-0 flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="h-8 w-8 rounded-xl bg-sky-500/10 text-sky-500 flex items-center justify-center font-bold">
                      <Edit3 className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white">AI-Drafted Customer Reply</h3>
                      <p className="text-[11px] text-slate-400 dark:text-neutral-500">
                        Grounded in historical resolutions • Never auto-sent without agent verification
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-bold text-sky-500">
                      {inference ? `Quality Score: ${(inference.draft.confidence * 100).toFixed(0)}%` : 'Manual Draft'}
                    </span>
                    <p className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">{replyText.length} / 280 chars</p>
                  </div>
                </div>

                {/* Safety Policy Flags Banner */}
                {inference?.safety && !inference.safety.passed && (
                  <div className="flex-shrink-0 mb-3 bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 text-xs text-rose-600 dark:text-rose-400">
                    <div className="font-bold flex items-center space-x-1.5 mb-0.5">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      <span>Safety Policy Warning Triggered</span>
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                      {inference.safety.flags.map((flag, i) => (
                        <li key={i}>{flag}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Draft Editable Text Area or Streaming Draft */}
                {isStreaming ? (
                  <div className="bg-slate-50 dark:bg-black border border-sky-500/30 rounded-xl p-4 min-h-[140px] mb-2">
                    <StreamingDraft
                      currentStage={currentStage}
                      streamedTokens={streamedTokens}
                      draftComplete={draftComplete}
                      safetyResult={sseSafetyResult}
                      pipelineComplete={ssePipelineComplete}
                      totalMs={sseTotalMs}
                      isStreaming={isStreaming}
                    />
                  </div>
                ) : (
                  <div className="relative flex-1 min-h-0 flex flex-col">
                    <textarea
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      placeholder="AI agent is drafting a reply..."
                      disabled={inferring || submittingAction}
                      className="w-full flex-1 p-3.5 text-sm bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-xl text-slate-900 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-600 focus:outline-none focus:ring-2 focus:ring-sky-500 leading-relaxed font-normal resize-none min-h-[130px]"
                    />
                  </div>
                )}

                {/* Inference Latency Metrics */}
                {inference && (
                  <div className="flex-shrink-0 mt-2.5 flex items-center justify-between text-[11px] text-slate-400 dark:text-neutral-500 font-mono">
                    <div className="flex items-center space-x-3">
                      <span className="bg-slate-100 dark:bg-neutral-800 px-2 py-0.5 rounded-full border border-slate-200 dark:border-neutral-800">
                        Latency: {inference.meta.latency_ms}ms
                      </span>
                      <span className="bg-slate-100 dark:bg-neutral-800 px-2 py-0.5 rounded-full border border-slate-200 dark:border-neutral-800">
                        Provider: {inference.meta.provider}
                      </span>
                    </div>
                    {inference.meta.safety_ms && (
                      <span className="bg-slate-100 dark:bg-neutral-800 px-2 py-0.5 rounded-full border border-slate-200 dark:border-neutral-800">
                        Safety: {inference.meta.safety_ms}ms
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Support Agent Action Buttons */}
              <div className="flex-shrink-0 pt-3.5 border-t border-slate-100 dark:border-neutral-800 mt-3.5">
                  <div className="flex flex-wrap gap-3 justify-end items-center">
                    <button
                      type="button"
                      disabled={submittingAction || isStreaming}
                      onClick={() => handleAction('reject')}
                      className="px-4 py-2 border border-slate-200 dark:border-neutral-800 text-slate-700 dark:text-neutral-300 hover:bg-slate-100 dark:hover:bg-neutral-800 text-xs font-bold rounded-full transition flex items-center space-x-1.5"
                    >
                      <UserX className="h-4 w-4 text-slate-400" />
                      <span>Reject Draft</span>
                    </button>

                    <button
                      type="button"
                      disabled={submittingAction || isStreaming}
                      onClick={() => handleAction('escalate')}
                      className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-full shadow transition flex items-center space-x-1.5"
                    >
                      <ShieldAlert className="h-4 w-4" />
                      <span>Escalate to Specialist</span>
                    </button>

                    <button
                      type="button"
                      disabled={submittingAction || isStreaming}
                      onClick={() => handleAction('edit')}
                      className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-full shadow transition flex items-center space-x-1.5"
                    >
                      <Edit3 className="h-4 w-4" />
                      <span>Edit & Send</span>
                    </button>

                    <button
                      type="button"
                      disabled={
                        submittingAction ||
                        isStreaming ||
                        (inference?.safety ? !inference.safety.passed : false) ||
                        (sseSafetyResult ? !sseSafetyResult.passed : false)
                      }
                      onClick={() => handleAction('approve')}
                      className="px-5 py-2 bg-sky-500 hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-bold rounded-full shadow transition flex items-center space-x-2"
                      title={
                        (inference?.safety && !inference.safety.passed) || (sseSafetyResult && !sseSafetyResult.passed)
                          ? "Disabled until all safety checks pass"
                          : "Approve draft and publish resolution"
                      }
                    >
                      <Send className="h-4 w-4" />
                      <span>Approve & Post</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      {/* Tab 2: Customer Twitter / X Thread View */}
      {activeTab === 'twitter' && (
        <div className="flex-1 overflow-y-auto p-6 flex justify-center">
          <div className="max-w-2xl w-full space-y-4">
            {/* Simulation Header Status Card */}
            <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800 p-4 shadow-sm flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-full bg-sky-500/10 flex items-center justify-center text-sky-500 font-bold">
                  <Twitter className="w-5 h-5 fill-current" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Twitter / X Conversation Simulator</h3>
                  <p className="text-xs text-slate-500 dark:text-neutral-400">
                    Live visualization of the public thread as rendered on the customer's timeline.
                  </p>
                </div>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                ticket.status === 'resolved'
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                  : ticket.status === 'escalated'
                  ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
                  : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
              }`}>
                {ticket.status === 'resolved'
                  ? 'Published on Twitter'
                  : ticket.status === 'escalated'
                  ? 'Escalated (Public Tweet Withheld)'
                  : 'Staged Draft Live Preview'}
              </span>
            </div>

            {/* Simulated X Tweet Thread */}
            <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800 shadow-sm overflow-hidden divide-y divide-slate-100 dark:divide-neutral-800">
              {/* 1. Customer Tweet Card */}
              <div className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm shadow-sm">
                      {(ticket.tweet_author || '@customer').replace('@', '').slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-sm font-bold text-slate-900 dark:text-white">Customer</span>
                        <span className="text-xs text-slate-400 dark:text-neutral-500 font-medium">{ticket.tweet_author || '@customer'}</span>
                      </div>
                      <p className="text-[11px] text-slate-400 dark:text-neutral-500">
                        {new Date(ticket.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • Twitter for iPhone
                      </p>
                    </div>
                  </div>
                </div>

                <p className="mt-3 text-base text-slate-900 dark:text-neutral-100 leading-relaxed font-normal">
                  <FormattedTweet text={ticket.customer_text} />
                </p>

                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-neutral-800 flex items-center justify-between text-xs text-slate-400 dark:text-neutral-500 max-w-md">
                  <div className="flex items-center space-x-1.5 hover:text-sky-500 transition cursor-pointer">
                    <MessageCircle className="w-4 h-4" />
                    <span>1</span>
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-emerald-500 transition cursor-pointer">
                    <Repeat className="w-4 h-4" />
                    <span>0</span>
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-rose-500 transition cursor-pointer">
                    <Heart className="w-4 h-4" />
                    <span>3</span>
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-sky-500 transition cursor-pointer">
                    <Bookmark className="w-4 h-4" />
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-sky-500 transition cursor-pointer">
                    <Share2 className="w-4 h-4" />
                  </div>
                </div>
              </div>

              {/* Thread Line Connector */}
              <div className="px-6 py-2 bg-slate-50/60 dark:bg-black/50 flex items-center space-x-3 text-xs text-slate-400 dark:text-neutral-500 border-t border-b border-slate-100 dark:border-neutral-800">
                <div className="w-10 flex justify-center">
                  <div className="w-0.5 h-6 bg-slate-200 dark:bg-neutral-800" />
                </div>
                <span className="text-[11px] text-slate-500 dark:text-neutral-400 italic">
                  Apple Support replied to <strong className="text-slate-700 dark:text-neutral-300">{ticket.tweet_author || '@customer'}</strong>
                </span>
              </div>

              {/* 2. Official @AppleSupport Verified Reply */}
              <div className="p-6 bg-white dark:bg-neutral-900">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-full bg-black dark:bg-white text-white dark:text-black flex items-center justify-center font-bold text-lg shadow-sm">
                      <Twitter className="w-5 h-5 fill-current" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-sm font-bold text-slate-900 dark:text-white">Apple Support</span>
                        <BadgeCheck className="w-4 h-4 text-sky-500 fill-sky-500/10" />
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                          Official Verified Brand
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 dark:text-neutral-500">
                        @AppleSupport • Replying to <span className="text-sky-500">{ticket.tweet_author || '@customer'}</span>
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-3 text-base text-slate-900 dark:text-neutral-100 leading-relaxed font-normal">
                  {replyText ? (
                    <FormattedTweet text={replyText} />
                  ) : (
                    <span className="italic text-slate-400 dark:text-neutral-500">
                      Draft is generating or waiting for agent review...
                    </span>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-neutral-800 flex items-center justify-between text-xs text-slate-400 dark:text-neutral-500 max-w-md">
                  <div className="flex items-center space-x-1.5 hover:text-sky-500 transition cursor-pointer">
                    <MessageCircle className="w-4 h-4" />
                    <span>Reply</span>
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-emerald-500 transition cursor-pointer">
                    <Repeat className="w-4 h-4" />
                    <span>Retweet</span>
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-rose-500 transition cursor-pointer">
                    <Heart className="w-4 h-4 text-rose-500 fill-rose-500/10" />
                    <span className="text-rose-500 font-bold">14</span>
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-sky-500 transition cursor-pointer">
                    <Bookmark className="w-4 h-4" />
                  </div>
                  <div className="flex items-center space-x-1.5 hover:text-sky-500 transition cursor-pointer">
                    <Share2 className="w-4 h-4" />
                  </div>
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800 p-4 shadow-sm flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-900 dark:text-white block">
                  {ticket.status === 'resolved' ? 'Delivered to Customer Timeline' : 'Live Staged Action'}
                </span>
                <span className="text-[11px] text-slate-500 dark:text-neutral-400">
                  {ticket.status === 'resolved'
                    ? 'This resolution is officially sent to the customer on Twitter and stored in Knowledge Base.'
                    : 'Review the simulated tweet above. You can approve it here or return to Cockpit for deep diagnostics.'}
                </span>
              </div>

              <div className="flex items-center space-x-2 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => setActiveTab('cockpit')}
                  className="px-4 py-2 text-xs font-bold text-slate-600 dark:text-neutral-400 hover:bg-slate-100 dark:hover:bg-neutral-800 rounded-full transition"
                >
                  Return to Cockpit
                </button>

                {ticket.status !== 'resolved' && (
                  <button
                    type="button"
                    onClick={() => handleAction('approve')}
                    disabled={submittingAction || !replyText}
                    className="px-5 py-2 bg-sky-500 hover:bg-sky-600 text-white text-xs font-bold rounded-full shadow transition flex items-center space-x-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>{submittingAction ? 'Publishing...' : 'Approve & Post to Twitter'}</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
