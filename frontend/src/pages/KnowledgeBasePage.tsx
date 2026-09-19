import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  CheckCircle2,
  Database,
  Filter,
  RefreshCw,
  Search,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  TrendingUp,
  Lock,
  Shield,
  Star,
} from 'lucide-react';
import { api } from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';
import { KnowledgeEntry, KnowledgeStats } from '../types';
import { FormattedTweet } from '../components/common/FormattedTweet';

export const KnowledgeBasePage: React.FC = () => {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

  const [loading, setLoading] = useState(true);
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIntent, setSelectedIntent] = useState<string>('all');
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [res, st] = await Promise.all([
        api.getKnowledgeEntries(selectedIntent !== 'all' ? selectedIntent : undefined),
        api.getKnowledgeStats(),
      ]);
      setEntries(res.items);
      setStats(st);
    } catch (err) {
      console.error('Failed to load knowledge base', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedIntent]);

  const handleToggle = async (entry: KnowledgeEntry) => {
    if (!isAdmin) {
      alert('Administrative Privileges Required: Only Operations Admins can enable or disable knowledge base entries from RAG retrieval.');
      return;
    }
    setTogglingId(entry.id);
    try {
      const updated = await api.toggleKnowledgeEntry(entry.id, !entry.is_active);
      setEntries((prev) =>
        prev.map((e) => (e.id === entry.id ? { ...e, is_active: updated.is_active } : e))
      );
    } catch (err) {
      console.error('Failed to toggle entry', err);
    } finally {
      setTogglingId(null);
    }
  };

  const filteredEntries = entries.filter((e) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      e.customer_message.toLowerCase().includes(q) ||
      e.resolution_text.toLowerCase().includes(q) ||
      (e.intent && e.intent.toLowerCase().includes(q))
    );
  });

  return (
    <div className="flex-1 h-full min-h-0 overflow-y-auto p-5 space-y-4 max-w-7xl mx-auto w-full text-slate-900 dark:text-neutral-100">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 tracking-tight">
            <BookOpen className="w-6 h-6 text-sky-500" />
            Knowledge Base & RAG Memory
          </h1>
          <p className="text-xs text-slate-500 dark:text-neutral-400 mt-0.5">
            Audit and manage learned solutions. Every agent approval automatically expands this vector store.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 text-slate-700 dark:text-neutral-300 rounded-full hover:bg-slate-50 dark:hover:bg-neutral-800 transition shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-500' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Role Authorization Notice Banner */}
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
              <strong>Tier-1 Support Agent View:</strong>
            )}{' '}
            {isAdmin
              ? 'You have full curation privileges to enable or disable historical solutions in live RAG retrieval.'
              : 'You can browse and search verified Apple Support resolutions. Toggling retrieval status requires an Operations Admin account.'}
          </span>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider text-[10px] border ${
          isAdmin 
            ? 'bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/30' 
            : 'bg-sky-500/20 text-sky-600 dark:text-sky-400 border-sky-500/30'
        }`}>
          {isAdmin ? 'Curation Mode' : 'Read-Only Mode'}
        </span>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Total Solutions</span>
            <Database className="w-4 h-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
            {stats ? stats.total_entries : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">Active RAG memory items</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Seed Dataset</span>
            <CheckCircle2 className="w-4 h-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
            {stats ? stats.from_original_dataset : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">Baseline AppleSupport data</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Agent Approved</span>
            <Sparkles className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-500 font-mono">
            {stats ? stats.from_agent_feedback : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">Learned from human reviews</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Self-Growth Rate</span>
            <TrendingUp className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-purple-500 font-mono">
            {stats ? `+${stats.growth_from_feedback_pct}%` : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">Expansion from feedback loop</span>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 dark:text-neutral-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search questions, resolutions, or keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-xs bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-full text-slate-900 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-sky-500 transition shadow-sm"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400 dark:text-neutral-500" />
          <select
            value={selectedIntent}
            onChange={(e) => setSelectedIntent(e.target.value)}
            className="text-xs bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 text-slate-900 dark:text-neutral-100 rounded-full px-3.5 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 transition shadow-sm"
          >
            <option value="all">All Intent Categories</option>
            <option value="battery_performance">Battery Performance</option>
            <option value="charging_issues">Charging Issues</option>
            <option value="ios_update_bugs">iOS Update Bugs</option>
            <option value="app_crashes">App Crashes</option>
            <option value="connectivity_wifi_bluetooth">Connectivity (Wi-Fi/Bluetooth)</option>
            <option value="icloud_sync_storage">iCloud Sync & Storage</option>
            <option value="apple_id_account">Apple ID & Account</option>
            <option value="hardware_damage">Hardware Damage</option>
            <option value="audio_speaker_mic">Audio / Speaker / Mic</option>
            <option value="display_screen">Display / Screen</option>
            <option value="performance_speed">Performance & Speed</option>
            <option value="purchase_refund_billing">Purchase / Refund / Billing</option>
            <option value="lost_device_find_my">Lost Device / Find My</option>
            <option value="out_of_scope">Out of Scope / Non-Apple</option>
          </select>
        </div>
      </div>

      {/* Entries List */}
      <div className="space-y-3">
        {filteredEntries.map((entry) => {
          const helpfulPct = Math.round((entry.helpfulness_ratio || 0.5) * 100);
          return (
            <div
              key={entry.id}
              className={`bg-white dark:bg-neutral-900 border rounded-2xl p-5 transition shadow-sm space-y-3 ${
                entry.is_active 
                  ? 'border-slate-200 dark:border-neutral-800' 
                  : 'border-slate-200/60 dark:border-neutral-800/60 opacity-60 bg-slate-50/50 dark:bg-black/50'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[11px] font-mono text-slate-400 dark:text-neutral-500">
                      #{entry.id.substring(0, 8)}
                    </span>
                    {entry.intent && (
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-sky-500/10 text-sky-500 capitalize border border-sky-500/20">
                        {entry.intent.replace(/_/g, ' ')}
                      </span>
                    )}
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border flex items-center space-x-1 ${
                        entry.source_type === 'agent_approved'
                          ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                          : 'bg-slate-100 dark:bg-neutral-800 text-slate-600 dark:text-neutral-400 border-transparent'
                      }`}
                    >
                      {entry.source_type === 'agent_approved' && <Star className="w-3 h-3 fill-current inline" />}
                      <span>{entry.source_type === 'agent_approved' ? 'Agent Approved' : 'Seed Dataset'}</span>
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-slate-900 dark:text-neutral-100 leading-relaxed">
                    "<FormattedTweet text={entry.customer_message} />"
                  </p>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <div className="text-xs font-bold text-slate-900 dark:text-white font-mono">
                      {helpfulPct}% Helpful
                    </div>
                    <span className="text-[10px] text-slate-400 dark:text-neutral-500 font-mono">
                      Retrieved {entry.times_retrieved}x
                    </span>
                  </div>

                  {isAdmin ? (
                    <button
                      onClick={() => handleToggle(entry)}
                      disabled={togglingId === entry.id}
                      title={entry.is_active ? 'Disable from RAG retrieval' : 'Enable in RAG retrieval'}
                      className="text-slate-400 dark:text-neutral-500 hover:text-sky-500 transition"
                    >
                      {entry.is_active ? (
                        <ToggleRight className="w-7 h-7 text-sky-500" />
                      ) : (
                        <ToggleLeft className="w-7 h-7 text-slate-300 dark:text-neutral-700" />
                      )}
                    </button>
                  ) : (
                    <div
                      title="Admin Only: Frontline agents cannot toggle RAG retrieval status."
                      className="flex items-center space-x-1 px-2.5 py-1 bg-slate-100 dark:bg-neutral-800 border border-slate-200 dark:border-neutral-700 rounded-full text-[11px] font-bold text-slate-500 dark:text-neutral-400 cursor-not-allowed"
                    >
                      <Lock className="w-3 h-3 text-slate-400 dark:text-neutral-500" />
                      <span>{entry.is_active ? 'Active' : 'Inactive'}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Verified Resolution */}
              <div className="bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-xl p-3.5 text-xs text-slate-800 dark:text-neutral-200 leading-relaxed font-sans">
                <span className="font-bold text-sky-500 block mb-1">
                  Verified Brand Resolution:
                </span>
                <FormattedTweet text={entry.resolution_text} />
              </div>
            </div>
          );
        })}

        {filteredEntries.length === 0 && !loading && (
          <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-8 text-center text-slate-500 dark:text-neutral-400">
            <BookOpen className="w-8 h-8 mx-auto mb-2 text-slate-300 dark:text-neutral-700" />
            <p className="text-sm font-bold text-slate-900 dark:text-white">No knowledge base solutions found.</p>
            <p className="text-xs text-slate-400 dark:text-neutral-500 mt-1">
              Try adjusting your search query or intent filter.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
