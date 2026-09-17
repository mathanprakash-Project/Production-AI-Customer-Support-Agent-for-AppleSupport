import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  DollarSign,
  Layers,
  RefreshCw,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { api } from '../services/apiClient';
import {
  AnalyticsOverview,
  FeedbackSummaryItem,
  IntentDistributionResponse,
  TimeSavedResponse,
} from '../types';

export const AnalyticsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [distribution, setDistribution] = useState<IntentDistributionResponse | null>(null);
  const [feedbackSummary, setFeedbackSummary] = useState<FeedbackSummaryItem[]>([]);
  const [timeSaved, setTimeSaved] = useState<TimeSavedResponse | null>(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [ov, dist, fb, ts] = await Promise.all([
        api.getAnalyticsOverview(),
        api.getIntentDistribution('week'),
        api.getFeedbackSummary(),
        api.getTimeSaved(),
      ]);
      setOverview(ov);
      setDistribution(dist);
      setFeedbackSummary(fb.summary);
      setTimeSaved(ts);
    } catch (err) {
      console.error('Failed to load analytics', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto w-full text-slate-900 dark:text-neutral-100">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2 tracking-tight">
            <BarChart3 className="w-6 h-6 text-sky-500" />
            Operations & Performance Analytics
          </h1>
          <p className="text-xs text-slate-500 dark:text-neutral-400 mt-0.5">
            Real-time pipeline metrics, agent approval rates, and labor cost efficiency.
          </p>
        </div>
        <button
          onClick={fetchAnalytics}
          disabled={loading}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 text-slate-700 dark:text-neutral-300 rounded-full hover:bg-slate-50 dark:hover:bg-neutral-800 transition shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-500' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Tickets Today</span>
            <Layers className="w-4 h-4 text-sky-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
            {overview ? overview.tickets_today : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">Past 24 hours</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Draft Approval</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-emerald-500 font-mono">
            {overview ? `${overview.draft_approval_rate}%` : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">Accepted by agents</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Avg Latency</span>
            <Zap className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
            {overview ? `${overview.avg_response_time_seconds}s` : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">5-stage pipeline</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Escalation Rate</span>
            <AlertTriangle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold text-rose-500 font-mono">
            {overview ? `${overview.escalation_rate}%` : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">Specialist handoffs</span>
        </div>

        <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-4 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 dark:text-neutral-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Time Saved</span>
            <Clock className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-purple-500 font-mono">
            {overview ? `${overview.time_saved_hours}h` : '—'}
          </div>
          <span className="text-[10px] text-slate-400 dark:text-neutral-500">vs 4.5m manual baseline</span>
        </div>
      </div>

      {/* Grid: Intent Distribution & ROI Calculations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Intent Distribution */}
        <div className="lg:col-span-2 bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-sky-500" />
              Customer Intent Distribution
            </h3>
            <span className="text-xs text-slate-400 dark:text-neutral-500 font-mono">
              Total: {distribution?.total_tickets || 0} tickets
            </span>
          </div>

          <div className="space-y-3 pt-2">
            {overview?.top_intents.map((item, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-700 dark:text-neutral-300 capitalize">
                    {item.name.replace(/_/g, ' ')}
                  </span>
                  <span className="font-mono text-slate-400 dark:text-neutral-500">
                    {item.count} tickets ({item.pct}%)
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-100 dark:bg-black rounded-full overflow-hidden">
                  <div
                    className="h-full bg-sky-500 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(item.pct, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ROI & Labor Cost Savings */}
        <div className="bg-slate-900 dark:bg-neutral-900 border border-slate-800 dark:border-neutral-800 text-white rounded-2xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-1.5">
                <DollarSign className="w-4 h-4 text-emerald-400" />
                Support Labor ROI
              </h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ACTIVE
              </span>
            </div>

            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-400">Estimated Labor Cost Savings</p>
                <p className="text-3xl font-extrabold text-emerald-400 mt-0.5 font-mono">
                  ${timeSaved?.estimated_cost_savings_usd.toFixed(2) || '0.00'}
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Based on $28.00/hr agent benchmark
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-400 block">Hours Saved</span>
                  <span className="text-base font-bold text-white font-mono">
                    {timeSaved?.hours_saved || 0} hrs
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Avg Edit Ratio</span>
                  <span className="text-base font-bold text-white font-mono">
                    {overview?.avg_edit_distance || 0.12}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-slate-800 text-[11px] text-slate-400 font-mono">
            Formula: (Tickets × 4.5m manual) - (Tickets × 30s review)
          </div>
        </div>
      </div>

      {/* Triage Breakdown Table */}
      <div className="bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-2xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-slate-100 dark:border-neutral-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            Agent Triage Breakdown by Intent Category
          </h3>
          <span className="text-xs text-slate-400 dark:text-neutral-500">Human-in-the-loop decisions</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-black text-slate-400 dark:text-neutral-500 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-neutral-800">
              <tr>
                <th className="px-5 py-3">Category</th>
                <th className="px-4 py-3 text-center">Approved</th>
                <th className="px-4 py-3 text-center">Edited</th>
                <th className="px-4 py-3 text-center">Rejected</th>
                <th className="px-4 py-3 text-center">Escalated</th>
                <th className="px-4 py-3 text-center">Total</th>
                <th className="px-5 py-3 text-right">Approval Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-neutral-800 text-slate-700 dark:text-neutral-300 font-medium">
              {feedbackSummary.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 dark:hover:bg-black/50 transition">
                  <td className="px-5 py-3 capitalize font-bold text-slate-900 dark:text-white">
                    {row.intent.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3 text-center text-emerald-500 font-mono font-bold">
                    {row.approved}
                  </td>
                  <td className="px-4 py-3 text-center text-sky-500 font-mono font-bold">
                    {row.edited}
                  </td>
                  <td className="px-4 py-3 text-center text-slate-400 dark:text-neutral-500 font-mono">
                    {row.rejected}
                  </td>
                  <td className="px-4 py-3 text-center text-rose-500 font-mono font-bold">
                    {row.escalated}
                  </td>
                  <td className="px-4 py-3 text-center font-mono text-slate-600 dark:text-neutral-400">
                    {row.total}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                        row.approval_rate >= 80
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                          : row.approval_rate >= 60
                          ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
                          : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
                      }`}
                    >
                      {row.approval_rate}%
                    </span>
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
