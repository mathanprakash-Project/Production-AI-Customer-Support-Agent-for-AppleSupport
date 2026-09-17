import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  TrendingUp,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Play,
  Lock,
  Shield,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';
import { EvalSummaryResponse } from '../types';

export const EvalDashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

  const [summary, setSummary] = useState<EvalSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const data = await api.getEvaluationSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to load eval summary', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleTriggerEval = async (smoke: boolean) => {
    if (!isAdmin) {
      alert('Administrative Privileges Required: Only Operations Admins can trigger model evaluation benchmarks.');
      return;
    }
    setTriggering(true);
    try {
      await api.triggerEvaluation(smoke);
      setTriggerMsg(`Evaluation job started in background (${smoke ? 'Smoke test 25 items' : 'Full 200 items'}). Refreshing metrics...`);
      setTimeout(() => {
        fetchSummary();
        setTriggerMsg(null);
      }, 3000);
    } catch (err) {
      console.error('Failed to trigger evaluation', err);
    } finally {
      setTriggering(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500 dark:text-neutral-400 text-sm">
        Loading evaluation metrics and benchmark dashboard...
      </div>
    );
  }

  if (!summary) {
    return <div className="p-8 text-center text-slate-500 dark:text-neutral-400">No evaluation runs recorded.</div>;
  }

  const { headline_metrics, baselines } = summary;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto w-full text-slate-900 dark:text-neutral-100">
      {/* Top Banner & Trigger Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-neutral-900 p-6 rounded-2xl border border-slate-200 dark:border-neutral-800 shadow-sm">
        <div>
          <div className="inline-flex items-center space-x-2 px-3 py-1 bg-sky-500/10 border border-sky-500/20 rounded-full text-xs font-bold text-sky-500 mb-2">
            <BarChart3 className="h-3.5 w-3.5" />
            <span>Golden Set Benchmark (200 Hand-Labelled Items)</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">AI Agent Evaluation Dashboard</h2>
          <p className="text-xs text-slate-500 dark:text-neutral-400 mt-0.5">
            Automated metrics, baseline comparisons, and human-judge agreement study for @AppleSupport.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleTriggerEval(true)}
            disabled={!isAdmin || triggering}
            title={!isAdmin ? 'Admin privileges required to trigger benchmarks' : 'Run 25-item smoke evaluation'}
            className={`px-4 py-2 text-xs font-bold rounded-full transition flex items-center space-x-1.5 ${
              isAdmin 
                ? 'bg-slate-100 dark:bg-neutral-800 hover:bg-slate-200 dark:hover:bg-neutral-700 text-slate-700 dark:text-neutral-200' 
                : 'bg-slate-100 dark:bg-neutral-800 text-slate-400 dark:text-neutral-600 cursor-not-allowed opacity-60'
            }`}
          >
            <Play className="w-3.5 h-3.5" />
            <span>Smoke Eval (25)</span>
          </button>

          <button
            onClick={() => handleTriggerEval(false)}
            disabled={!isAdmin || triggering}
            title={!isAdmin ? 'Admin privileges required to trigger benchmarks' : 'Run full 200-item benchmark'}
            className={`px-4 py-2 text-xs font-bold rounded-full transition flex items-center space-x-1.5 shadow ${
              isAdmin 
                ? 'bg-sky-500 hover:bg-sky-600 text-white' 
                : 'bg-slate-300 dark:bg-neutral-800 text-slate-500 dark:text-neutral-600 cursor-not-allowed opacity-60'
            }`}
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>{triggering ? 'Running...' : 'Run Full Benchmark (200)'}</span>
          </button>
        </div>
      </div>

      {triggerMsg && (
        <div className="bg-sky-500/10 border border-sky-500/20 text-sky-600 dark:text-sky-400 text-xs py-2.5 px-4 rounded-xl font-bold">
          {triggerMsg}
        </div>
      )}

      {/* Role Notice */}
      <div className={`p-4 rounded-2xl border flex items-center justify-between text-xs ${
        isAdmin 
          ? 'bg-purple-500/10 border-purple-500/20 text-purple-700 dark:text-purple-300' 
          : 'bg-sky-500/10 border-sky-500/20 text-sky-700 dark:text-sky-300'
      }`}>
        <div className="flex items-center space-x-3">
          {isAdmin ? (
            <Shield className="w-4 h-4 text-purple-500 flex-shrink-0" />
          ) : (
            <Lock className="w-4 h-4 text-sky-500 flex-shrink-0" />
          )}
          <span>
            {isAdmin ? (
              <strong>Operations Admin Access:</strong>
            ) : (
              <strong>Auditor / Agent Read-Only Mode:</strong>
            )}{' '}
            {isAdmin
              ? 'You have execution clearance to trigger model evaluation benchmarks and update accuracy baselines.'
              : 'You can review accuracy benchmarks and failure diagnostics. Triggering model evaluation runs requires an Operations Admin account.'}
          </span>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider text-[10px] border ${
          isAdmin 
            ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/30' 
            : 'bg-sky-500/20 text-sky-600 dark:text-sky-400 border-sky-500/30'
        }`}>
          {isAdmin ? 'Admin Clearance' : 'Read-Only'}
        </span>
      </div>

      {/* Headline Metric Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Intent Accuracy</span>
            <CheckCircle2 className="w-4 h-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
            {(headline_metrics.accuracy * 100).toFixed(1)}%
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">Taxonomy classification</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Macro F1</span>
            <TrendingUp className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-purple-500 font-mono">
            {(headline_metrics.macro_f1 * 100).toFixed(1)}%
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">Multi-class balance</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Escalation F1</span>
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-500 font-mono">
            {(headline_metrics.escalation_f1 * 100).toFixed(1)}%
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">Safety handoff score</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">ROUGE-L</span>
            <AlertOctagon className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-amber-500 font-mono">
            {(headline_metrics.rouge_l * 100).toFixed(1)}%
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">RAG ground truth match</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">p50 Latency</span>
            <Clock className="w-4 h-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
            {headline_metrics.latency_p50_ms || 12}ms
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">p50 pipeline response</span>
        </div>
      </div>

      {/* Baseline Comparisons Table */}
      <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-neutral-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Model Baseline Comparison (A/B Metric Evaluation)
          </h3>
          <span className="text-xs text-slate-400 dark:text-neutral-500 font-mono">Target: Ollama 3.2 3B vs Mocks</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-black text-slate-400 dark:text-neutral-500 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-neutral-800">
              <tr>
                <th className="px-5 py-3">Model Variant</th>
                <th className="px-4 py-3 text-center">Intent Accuracy</th>
                <th className="px-4 py-3 text-center">Macro F1</th>
                <th className="px-4 py-3 text-center">Escalation F1</th>
                <th className="px-4 py-3 text-center">ROUGE-L Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-neutral-800 text-slate-700 dark:text-neutral-300 font-medium">
              {Object.entries(baselines).map(([modelName, metric], idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 dark:hover:bg-black/50 transition">
                  <td className="px-5 py-3 font-bold text-slate-900 dark:text-white">
                    {modelName}
                  </td>
                  <td className="px-4 py-3 text-center text-sky-500 font-mono font-bold">
                    {(metric.accuracy * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-center text-purple-500 font-mono font-bold">
                    {(metric.macro_f1 * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-center text-emerald-500 font-mono font-bold">
                    {(metric.escalation_f1 * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-center text-amber-500 font-mono font-bold">
                    {(metric.rouge_l * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
