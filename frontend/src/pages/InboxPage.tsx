import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Inbox,
  Plus,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Search,
  ChevronRight,
  ShieldAlert,
  Sparkles,
  MessageSquare,
} from 'lucide-react';
import { api } from '../services/apiClient';
import { useAuthStore } from '../stores/authStore';
import { Ticket, TicketStatus } from '../types';
import { FormattedTweet } from '../components/common/FormattedTweet';

export const InboxPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCustomerText, setNewCustomerText] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const data = await api.getTickets(statusFilter);
      setTickets(data.items);
    } catch (err) {
      console.error('Failed to load tickets', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [statusFilter]);

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCustomerText.trim()) return;
    setCreating(true);
    try {
      const newTicket = await api.createTicket(newCustomerText);
      setIsModalOpen(false);
      setNewCustomerText('');
      navigate(`/inbox/${newTicket.id}`);
    } catch (err) {
      console.error('Failed to create ticket', err);
    } finally {
      setCreating(false);
    }
  };

  const getStatusBadge = (status: TicketStatus) => {
    switch (status) {
      case 'open':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
            <Clock className="h-3 w-3 mr-1" /> Open
          </span>
        );
      case 'drafted':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
            <Sparkles className="h-3 w-3 mr-1" /> AI Drafted
          </span>
        );
      case 'resolved':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3 mr-1" /> Published
          </span>
        );
      case 'escalated':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            <ShieldAlert className="h-3 w-3 mr-1" /> Escalated
          </span>
        );
    }
  };

  const filteredTickets = tickets.filter((t) =>
    t.customer_text.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex-1 h-full min-h-0 flex flex-col overflow-hidden bg-slate-50 dark:bg-black text-slate-900 dark:text-neutral-100 animate-fade-in">
      {/* Top Header */}
      <header className="flex-shrink-0 bg-white dark:bg-black border-b border-slate-200 dark:border-neutral-800 px-6 py-4 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Support Ticket Queue
            </h2>
            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border ${
              isAdmin 
                ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20' 
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
            }`}>
              {isAdmin ? 'Supervisor Queue' : 'Agent Triage Queue'}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-neutral-400 mt-1">
            {isAdmin 
              ? 'Supervisory ticket oversight, audit logs, and high-risk customer escalations.'
              : 'Live incoming customer inquiries for @AppleSupport. Review, edit, and publish AI drafts.'}
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-500 hover:bg-sky-600 text-white text-xs font-bold rounded-full shadow-sm transition-all"
        >
          <Plus className="h-4 w-4" />
          <span>Simulate Customer Tweet</span>
        </button>
      </header>

      {/* Filter and Search Toolbar */}
      <div className="flex-shrink-0 bg-white dark:bg-black border-b border-slate-200 dark:border-neutral-800 px-6 py-2.5 flex items-center justify-between gap-4">
        {/* Filter Tabs - X Style */}
        <div className="flex items-center space-x-1">
          {['all', 'open', 'drafted', 'resolved', 'escalated'].map((tab) => {
            const isEscalatedTab = tab === 'escalated';
            const isActive = statusFilter === tab;
            return (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold capitalize transition-all flex items-center space-x-1.5 ${
                  isActive
                    ? isEscalatedTab
                      ? 'bg-rose-600 text-white font-bold shadow-sm'
                      : 'bg-slate-900 dark:bg-white text-white dark:text-black font-bold'
                    : isEscalatedTab
                      ? 'text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 font-bold'
                      : 'text-slate-600 dark:text-neutral-400 hover:bg-slate-100 dark:hover:bg-neutral-900'
                }`}
              >
                <span>{tab}</span>
                {isEscalatedTab && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold uppercase ${
                    isActive ? 'bg-rose-900 text-white' : 'bg-rose-500/20 text-rose-600 dark:text-rose-400'
                  }`}>
                    {isAdmin ? 'Review' : 'Alert'}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Search input */}
        <div className="relative w-72">
          <Search className="absolute left-3.5 top-2.5 h-3.5 w-3.5 text-slate-400 dark:text-neutral-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search tickets by content..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-100 dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-full text-slate-900 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>
      </div>

      {/* Ticket List / Feed */}
      <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-slate-400 dark:text-neutral-500 text-sm">
            Loading ticket queue...
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="text-center py-16 bg-white dark:bg-neutral-900 rounded-2xl border border-slate-200 dark:border-neutral-800">
            <MessageSquare className="mx-auto h-12 w-12 text-slate-300 dark:text-neutral-700" />
            <h3 className="mt-3 text-sm font-bold text-slate-900 dark:text-white">No tickets found</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-neutral-400 max-w-sm mx-auto">
              There are no customer inquiries matching your filter criteria.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredTickets.map((ticket) => (
              <div
                key={ticket.id}
                onClick={() => navigate(`/inbox/${ticket.id}`)}
                className="bg-white dark:bg-neutral-900 hover:border-sky-400 dark:hover:border-sky-500 hover:shadow-md cursor-pointer border border-slate-200 dark:border-neutral-800 rounded-2xl p-5 transition-all duration-200 shadow-sm flex items-center justify-between group"
              >
                <div className="flex-1 pr-6">
                  <div className="flex items-center space-x-3 mb-2">
                    {getStatusBadge(ticket.status)}
                    <span className="text-[11px] font-mono text-slate-400 dark:text-neutral-500">
                      #{ticket.id.slice(0, 8)}
                    </span>
                    <span className="text-[11px] text-slate-400 dark:text-neutral-500">
                      {new Date(ticket.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-slate-900 dark:text-neutral-100 leading-relaxed group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors line-clamp-2">
                    <FormattedTweet text={ticket.customer_text} />
                  </p>
                </div>
                <div className="flex items-center text-slate-300 dark:text-neutral-700 group-hover:text-sky-500 transition-colors">
                  <ChevronRight className="h-5 w-5" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Inbound Tweet Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-neutral-900 rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 dark:border-neutral-800">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-1">
              Simulate Inbound Customer Tweet
            </h3>
            <p className="text-xs text-slate-500 dark:text-neutral-400 mb-4 leading-relaxed">
              Enter any inquiry to execute the AI agent pipeline (intent classification, pgvector historical grounding, safety check, and escalation detection).
            </p>

            <form onSubmit={handleCreateTicket}>
              <textarea
                rows={4}
                value={newCustomerText}
                onChange={(e) => setNewCustomerText(e.target.value)}
                placeholder="e.g., @AppleSupport My iPhone 14 stopped charging overnight. It vibrates when plugged in but won't take charge."
                required
                className="w-full p-3.5 text-sm bg-slate-50 dark:bg-black border border-slate-200 dark:border-neutral-800 rounded-xl text-slate-900 dark:text-neutral-100 placeholder-slate-400 dark:placeholder-neutral-600 focus:outline-none focus:ring-2 focus:ring-sky-500 mb-4"
              />

              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 dark:text-neutral-400 hover:bg-slate-100 dark:hover:bg-neutral-800 rounded-full transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-5 py-2 bg-sky-500 hover:bg-sky-600 text-white text-xs font-bold rounded-full shadow transition"
                >
                  {creating ? 'Ingesting...' : 'Ingest Tweet & Open Ticket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
