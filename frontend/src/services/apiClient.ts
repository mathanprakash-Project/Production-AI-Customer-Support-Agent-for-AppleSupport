import axios from 'axios';
import {
  EvalSummaryResponse,
  InferenceResponse,
  IntentItem,
  Ticket,
  User,
  AnalyticsOverview,
  IntentDistributionResponse,
  ConfidenceTrendResponse,
  FeedbackSummaryResponse,
  TimeSavedResponse,
  KnowledgeEntry,
  KnowledgeStats,
} from '../types';

const API_BASE = '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 180000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token automatically
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// API helper functions
export const api = {
  // Auth
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await apiClient.post('/auth/login', { email, password });
    return res.data;
  },

  // Tickets
  async getTickets(status?: string, page = 1, size = 50): Promise<{ items: Ticket[]; total: number }> {
    const params: Record<string, any> = { page, size };
    if (status && status !== 'all') params.status = status;
    const res = await apiClient.get('/tickets', { params });
    return res.data;
  },

  async getTicket(id: string): Promise<Ticket> {
    const res = await apiClient.get(`/tickets/${id}`);
    return res.data;
  },

  async createTicket(customer_text: string, tweet_author = '@customer'): Promise<Ticket> {
    const res = await apiClient.post('/tickets', { customer_text, tweet_author });
    return res.data;
  },

  // Inference
  async runInference(ticketId: string, refresh = false): Promise<InferenceResponse> {
    const res = await apiClient.post(`/tickets/${ticketId}/inference`, null, {
      params: { refresh },
    });
    return res.data;
  },

  // Feedback & Learning Loop
  async submitFeedback(
    ticketId: string,
    action: 'approve' | 'edit' | 'reject' | 'escalate',
    edited_text?: string,
    notes?: string,
    final_response_text?: string,
    review_time_seconds?: number
  ) {
    const res = await apiClient.post(`/tickets/${ticketId}/feedback`, {
      action,
      edited_text,
      notes,
      final_response_text,
      review_time_seconds,
    });
    return res.data;
  },

  // Analytics
  async getAnalyticsOverview(): Promise<AnalyticsOverview> {
    const res = await apiClient.get('/analytics/overview');
    return res.data;
  },

  async getIntentDistribution(period = 'week'): Promise<IntentDistributionResponse> {
    const res = await apiClient.get('/analytics/intent-distribution', { params: { period } });
    return res.data;
  },

  async getConfidenceTrend(): Promise<ConfidenceTrendResponse> {
    const res = await apiClient.get('/analytics/confidence-over-time');
    return res.data;
  },

  async getFeedbackSummary(): Promise<FeedbackSummaryResponse> {
    const res = await apiClient.get('/analytics/feedback-summary');
    return res.data;
  },

  async getTimeSaved(): Promise<TimeSavedResponse> {
    const res = await apiClient.get('/analytics/time-saved');
    return res.data;
  },

  // Knowledge Base
  async getKnowledgeEntries(intent?: string, page = 1, size = 20): Promise<{ items: KnowledgeEntry[]; total: number }> {
    const params: Record<string, any> = { page, size };
    if (intent && intent !== 'all') params.intent = intent;
    const res = await apiClient.get('/knowledge', { params });
    return res.data;
  },

  async getKnowledgeStats(): Promise<KnowledgeStats> {
    const res = await apiClient.get('/knowledge/stats');
    return res.data;
  },

  async toggleKnowledgeEntry(id: string, is_active: boolean): Promise<KnowledgeEntry> {
    const res = await apiClient.patch(`/knowledge/${id}`, { is_active });
    return res.data;
  },

  // Intents
  async getIntents(): Promise<IntentItem[]> {
    const res = await apiClient.get('/intents');
    return res.data;
  },

  // Evaluation
  async getEvaluationSummary(): Promise<EvalSummaryResponse> {
    const res = await apiClient.get('/evaluation/latest');
    return res.data;
  },

  async triggerEvaluation(smoke = false) {
    const res = await apiClient.post('/evaluation/runs', null, { params: { smoke } });
    return res.data;
  },

  // Health
  async getHealth() {
    const res = await apiClient.get('/health');
    return res.data;
  },
};

