export type Role = 'agent' | 'admin' | 'manager';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export type TicketStatus = 'open' | 'drafted' | 'resolved' | 'escalated';

export interface Ticket {
  id: string;
  customer_text: string;
  tweet_author?: string;
  source_tweet_id?: string;
  status: TicketStatus;
  assigned_to?: string;
  intent?: string;
  confidence?: number;
  sentiment_score?: number;
  is_escalated?: boolean;
  escalation_reason?: string;
  pii_detected?: boolean;
  total_pipeline_time_ms?: number;
  created_at: string;
  processed_at?: string;
  resolved_at?: string;
  updated_at: string;
}

export interface IntentAlternative {
  label: string;
  confidence: number;
}

export interface IntentClassification {
  intent: string;
  confidence: number;
  reasoning?: string;
  alternatives: IntentAlternative[];
}

export interface RetrievedThreadItem {
  thread_id: string;
  similarity: number;
  customer_msg: string;
  brand_reply: string;
  intent_label?: string;
}

export interface DraftReply {
  reply: string;
  confidence: number;
  grounded_thread_ids: string[];
  reasoning?: string;
}

export interface EscalationDecision {
  decision: 'auto' | 'escalate';
  reasons: string[];
  risk_score: number;
}

export interface SafetyResult {
  passed: boolean;
  flags: string[];
}

export interface InferenceMeta {
  model: string;
  provider: string;
  prompt_version: string;
  latency_ms: number;
  tokens_prompt: number;
  tokens_completion: number;
  classification_ms?: number;
  escalation_ms?: number;
  retrieval_ms?: number;
  drafting_ms?: number;
  safety_ms?: number;
}

export interface InferenceResponse {
  ticket_id: string;
  customer_message: string;
  intent: IntentClassification;
  retrieved: RetrievedThreadItem[];
  draft: DraftReply;
  escalation: EscalationDecision;
  meta: InferenceMeta;
  safety?: SafetyResult;
  draft_id?: string;
}

export interface KnowledgeEntry {
  id: string;
  source_type: string;
  source_ticket_id?: string;
  customer_message: string;
  resolution_text: string;
  intent?: string;
  times_retrieved: number;
  times_helpful: number;
  helpfulness_ratio?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeStats {
  total_entries: number;
  from_original_dataset: number;
  from_agent_feedback: number;
  growth_from_feedback_pct: number;
}

export interface TopIntentMetric {
  name: string;
  count: number;
  pct: number;
}

export interface AnalyticsOverview {
  tickets_today: number;
  draft_approval_rate: number;
  avg_response_time_seconds: number;
  escalation_rate: number;
  time_saved_hours: number;
  avg_edit_distance: number;
  knowledge_base_size: number;
  top_intents: TopIntentMetric[];
}

export interface IntentDistributionResponse {
  period: string;
  total_tickets: number;
  distribution: TopIntentMetric[];
}

export interface ConfidenceTrendPoint {
  date: string;
  avg_confidence: number;
  ticket_count: number;
}

export interface ConfidenceTrendResponse {
  points: ConfidenceTrendPoint[];
}

export interface FeedbackSummaryItem {
  intent: string;
  approved: number;
  edited: number;
  rejected: number;
  escalated: number;
  total: number;
  approval_rate: number;
}

export interface FeedbackSummaryResponse {
  summary: FeedbackSummaryItem[];
}

export interface TimeSavedResponse {
  total_approved_drafts: number;
  hours_saved: number;
  estimated_cost_savings_usd: number;
  manual_baseline_minutes_per_ticket: number;
  ai_assisted_review_minutes_per_ticket: number;
  formula: string;
}

export interface IntentItem {
  label: string;
  description: string;
  examples: string[];
  count: number;
}

export interface BaselineMetric {
  accuracy: number;
  macro_f1: number;
  rouge_l: number;
  escalation_f1: number;
  latency_p50_ms?: number;
}

export interface JudgeDimension {
  cohens_kappa_quadratic: number;
  spearman_rho: number;
  human_mean: number;
  judge_mean: number;
}

export interface FailureExample {
  id: string;
  customer_message: string;
  expected_intent: string;
  predicted_intent: string;
  confidence: number;
  escalation_decision: string;
}

export interface EvalSummaryResponse {
  headline_metrics: BaselineMetric;
  per_class_f1: Record<string, number>;
  baselines: Record<string, BaselineMetric>;
  judge_agreement: Record<string, JudgeDimension>;
  failure_examples: FailureExample[];
}

