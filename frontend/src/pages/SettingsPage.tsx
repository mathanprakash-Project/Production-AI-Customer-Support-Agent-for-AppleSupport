import React, { useEffect, useState } from 'react';
import { Settings, Cpu, Shield, Database, CheckCircle2, AlertCircle, Lock } from 'lucide-react';
import { api } from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';

export const SettingsPage: React.FC = () => {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await api.getHealth();
        setHealth(data);
      } catch (err) {
        console.error('Failed to load health info', err);
      } finally {
        setLoading(false);
      }
    };
    fetchHealth();
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto w-full text-slate-900 dark:text-neutral-100">
      {/* Header */}
      <div className="bg-white dark:bg-neutral-900 p-6 rounded-2xl border border-slate-200 dark:border-neutral-800 shadow-sm">
        <div className="inline-flex items-center space-x-2 px-3 py-1 bg-sky-500/10 border border-sky-500/20 rounded-full text-xs font-bold text-sky-500 mb-2">
          <Settings className="h-3.5 w-3.5" />
          <span>System Configuration & Policies</span>
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">System Architecture & Rules</h2>
        <p className="text-xs text-slate-500 dark:text-neutral-400 mt-0.5">
          Active model parameters, vector database connectivity, and safety escalation policies.
        </p>
      </div>

      {/* Role Authorization Notice Banner */}
      <div className={`p-4 rounded-2xl border flex items-center justify-between text-xs ${
        isAdmin 
          ? 'bg-purple-500/10 border-purple-500/20 text-purple-700 dark:text-purple-300' 
          : 'bg-slate-100 dark:bg-neutral-900 border-slate-200 dark:border-neutral-800 text-slate-700 dark:text-neutral-300'
      }`}>
        <div className="flex items-center space-x-3">
          {isAdmin ? (
            <Shield className="w-4 h-4 text-purple-500 flex-shrink-0" />
          ) : (
            <Lock className="w-4 h-4 text-slate-400 dark:text-neutral-500 flex-shrink-0" />
          )}
          <span>
            {isAdmin ? (
              <strong>Operations Admin Access:</strong>
            ) : (
              <strong>Tier-1 Support Agent View:</strong>
            )}{' '}
            {isAdmin
              ? 'You have administrative control over model providers, escalation cutoffs, and safety keyword policies.'
              : 'You have read-only visibility into the active model configuration and guardrail rules.'}
          </span>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider text-[10px] border ${
          isAdmin 
            ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/30' 
            : 'bg-slate-200 dark:bg-neutral-800 text-slate-600 dark:text-neutral-400 border-transparent'
        }`}>
          {isAdmin ? 'System Lead' : 'Read-Only Audit'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* LLM & Model Settings */}
        <div className="bg-white dark:bg-neutral-900 p-6 rounded-2xl border border-slate-200 dark:border-neutral-800 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 text-slate-900 dark:text-white font-bold text-base">
            <Cpu className="h-5 w-5 text-sky-500" />
            <h3>GenAI / LLM Architecture</h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">Provider:</span>
              <span className="font-bold text-slate-900 dark:text-white uppercase font-mono">
                {health?.llm_provider?.name || 'ollama'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">Active Task Model:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono">
                {health?.llm_provider?.model || 'llama3.2:3b'}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">Evaluator / Judge Model:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono">qwen2.5:14b-instruct</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">Embeddings:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono">all-MiniLM-L6-v2 (384d)</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400 dark:text-neutral-500">Provider Status:</span>
              <span className="inline-flex items-center font-bold text-emerald-500">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Connected
              </span>
            </div>
          </div>
        </div>

        {/* Database & RAG Settings */}
        <div className="bg-white dark:bg-neutral-900 p-6 rounded-2xl border border-slate-200 dark:border-neutral-800 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 text-slate-900 dark:text-white font-bold text-base">
            <Database className="h-5 w-5 text-sky-500" />
            <h3>Database & Vector Store</h3>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">Database Engine:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono">PostgreSQL (pgvector)</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">Distance Metric:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono">Cosine Similarity</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">RAG Top-K Retrieval:</span>
              <span className="font-bold text-slate-900 dark:text-white font-mono">3 Matches</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-100 dark:border-neutral-800">
              <span className="text-slate-400 dark:text-neutral-500">Helpfulness Re-weighting:</span>
              <span className="font-bold text-emerald-500 font-mono">Enabled (0.7 sim + 0.3 helpful)</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400 dark:text-neutral-500">DB Connection:</span>
              <span className="inline-flex items-center font-bold text-emerald-500">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Healthy
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
