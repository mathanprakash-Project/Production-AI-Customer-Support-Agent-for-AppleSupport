# 🍎⚡ Apple Support AI Co-Pilot — v2.0 Restructure Plan

> **Goal**: Transform the current 4-stage CLI+API pipeline into a **production-grade 7-stage AI Co-Pilot** with self-updating knowledge base, feedback loop, analytics dashboard, safety checker, and scientific evaluation — all deployable with one Docker command.

---

## Current State Summary (v1.0)

Your existing codebase is **well-architected** with clean separation (repositories → services → API routers → schemas → models). Here's what already exists vs. what the v2.0 plan requires:

| Component | v1.0 Status | v2.0 Target |
|---|---|---|
| 4-stage pipeline (classify → retrieve → draft → escalate) | ✅ Working | Reorder + add 2 stages |
| Stage 5: Safety Checker | ❌ Missing | New `pipeline/safety_checker.py` |
| Stage 6: Agent Review (Human-in-Loop) | ⚠️ Partial (feedback exists) | Enhance with edit-distance tracking |
| Stage 7: Feedback Processor (Background) | ⚠️ Basic feedback service | Full feedback loop + KB auto-populate |
| Knowledge Base model + self-updating RAG | ❌ Missing | New model, service, retriever ranking |
| Analytics Service + Dashboard | ❌ Missing | New service, API routes, React page |
| Safety keywords YAML + URL/promise blocking | ❌ Missing | New deterministic + LLM checks |
| Helpfulness-weighted retrieval ranking | ❌ Missing | Enhanced retriever with formula |
| Intent taxonomy (12 categories) | ⚠️ Different names | Rename to match v2.0 spec |
| Golden test set (50 manually labeled) | ⚠️ Has 200-sample set | Reformat to v2.0 JSON schema |
| Docker Compose (4 services) | ✅ Working | Update DB name + add env vars |
| README with eval results table | ⚠️ Exists but outdated | Complete rewrite |

---

## User Review Required

> [!IMPORTANT]
> **Pipeline Stage Reordering**: Your v2.0 plan moves Escalation to **Stage 2** (before RAG retrieval), while v1.0 has it at Stage 4 (after drafting). This is a significant logic change — escalated tickets will skip RAG retrieval and drafting entirely, saving LLM calls. The plan below follows your v2.0 ordering.

> [!IMPORTANT]
> **Intent Category Renaming**: Your v1.0 uses names like `iphone_wont_charge`, `battery_drain`, `apple_id_account_access`. Your v2.0 plan uses `battery_performance`, `charging_issues`, `apple_id_account`. This affects the classifier prompt, golden test set labels, escalation rules, and frontend display. The plan includes a migration for this.

> [!WARNING]
> **Database Name Change**: Your v2.0 plan uses `apple_copilot` as the PostgreSQL DB name (v1.0 uses `tweetsupport`). This will require recreating the Docker volume or running a migration. I'll keep `tweetsupport` for continuity unless you want the rename.

> [!IMPORTANT]
> **Incremental vs. Big-Bang Approach**: Rather than rewriting the entire project from scratch (risking breaking the working v1.0), I'll take an **incremental approach** — adding new components alongside existing ones and refactoring in-place. This means the project stays runnable throughout.

---

## Open Questions

1. **Database name**: Keep `tweetsupport` (current) or rename to `apple_copilot` (v2.0 plan)?
2. **Frontend framework**: Your v2.0 plan mentions JSX components. The current frontend uses **TypeScript TSX**. Should I keep TSX (recommended) or convert to JSX?
3. **Celery vs BackgroundTasks**: Your v2.0 plan mentions both. For local development simplicity, I recommend **FastAPI BackgroundTasks** first, with Celery as a future add-on. Agreed?
4. **Existing pages**: The current frontend has `EvalDashboardPage`, `IntentsPage`, `SettingsPage` which aren't in the v2.0 plan. Should I keep them alongside the new pages, or replace them?

---

## Proposed Changes

### Phase 1 — New Database Models & Backend Services (Week 1-2)

This phase adds the 4 new tables and 3 new services required by v2.0, without breaking existing functionality.

---

#### Backend Models

##### [NEW] [knowledge_base.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/knowledge_base.py)
- New SQLAlchemy model `KnowledgeEntry` with fields: `id`, `source_type` (seed_dataset/agent_approved/manual_upload), `source_ticket_id`, `customer_message`, `resolution_text`, `intent`, `embedding` (Vector(384)), `times_retrieved`, `times_helpful`, `helpfulness_ratio`, `is_active`, `created_at`, `updated_at`
- Indexes on `intent`, `is_active`, and HNSW vector index on `embedding`

##### [NEW] [escalation_log.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/escalation_log.py)
- New model `EscalationLog` with: `id`, `ticket_id` (FK), `escalation_reasons` (JSON), `risk_score`, `escalated_by` (system/agent), `created_at`

##### [NEW] [analytics_daily.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/analytics_daily.py)
- New model `AnalyticsDaily` with: `id`, `date` (unique), `total_tickets`, `drafts_approved`, `drafts_edited`, `drafts_rejected`, `escalated_count`, `avg_confidence`, `avg_edit_distance`, `avg_pipeline_time_ms`, `avg_review_time_seconds`, `kb_entries_added`

##### [NEW] [system_config.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/system_config.py)
- New model `SystemConfig` with: `key` (PK), `value` (JSON), `description`, `updated_at`
- Used for configurable thresholds (escalation confidence, safety keywords, etc.)

##### [MODIFY] [ticket.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/ticket.py)
- Add new fields: `tweet_author`, `sentiment_score`, `pii_detected`, `pii_redacted_text`, `classification_time_ms`, `retrieval_time_ms`, `drafting_time_ms`, `total_pipeline_time_ms`, `processed_at`, `resolved_at`
- Add new status values: `pending`, `processing`, `draft_ready` (alongside existing `open`, `drafted`, `resolved`, `escalated`)

##### [MODIFY] [draft.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/draft.py)
- Add fields: `safety_passed` (bool), `safety_flags` (JSON), `response_type` (tweet/dm), `char_count`

##### [MODIFY] [feedback.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/feedback.py)
- Add fields: `edit_distance_ratio` (float), `review_time_seconds` (int), `final_response_text` (Text)

##### [MODIFY] [\_\_init\_\_.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/models/__init__.py)
- Register new models: `KnowledgeEntry`, `EscalationLog`, `AnalyticsDaily`, `SystemConfig`

---

#### Backend Services

##### [NEW] [knowledge_service.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/services/knowledge_service.py)
- `KnowledgeService` class with methods:
  - `seed_from_csv(csv_path)`: Batch-import threads from seed CSV into `knowledge_base` with embeddings
  - `add_from_approved_feedback(ticket, approved_text)`: Auto-populate KB from agent approvals
  - `get_entries(intent_filter, page, size)`: Paginated KB browser
  - `toggle_entry(entry_id, is_active)`: Activate/deactivate entries
  - `get_stats()`: KB health metrics (total, from_seed, from_feedback, growth%)

##### [NEW] [analytics_service.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/services/analytics_service.py)
- `AnalyticsService` class with methods:
  - `get_overview()`: Total tickets, approval rate, avg edit distance, avg pipeline time, escalation rate, time saved estimate
  - `get_intent_distribution(period)`: Intent breakdown for charts
  - `get_confidence_trend()`: Confidence scores over time
  - `get_feedback_summary()`: Approval/edit/reject rates by intent
  - `get_time_saved()`: Estimated agent time saved (formula: `approved_count * 4.5min - approved_count * avg_review_time`)
  - `compute_daily_snapshot()`: Background job to pre-compute `analytics_daily`

##### [MODIFY] [feedback_service.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/services/feedback_service.py)
- Enhance `record_feedback()` to:
  1. Calculate `edit_distance_ratio` using `difflib.SequenceMatcher`
  2. Store `final_response_text` and `review_time_seconds`
  3. Call `KnowledgeService.add_from_approved_feedback()` when action is `approve` or `edit`
  4. Call `_update_helpfulness()` to update retrieval source entry metrics
  5. Log to `EscalationLog` when action is `escalate`

---

#### Backend API Routes

##### [NEW] [knowledge.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/api/v1/knowledge.py)
- `GET /api/v1/knowledge` — Paginated knowledge base entries with intent filter
- `GET /api/v1/knowledge/stats` — KB health metrics
- `POST /api/v1/knowledge/seed` — Trigger CSV seed import (admin only)
- `PATCH /api/v1/knowledge/{id}` — Toggle entry active/inactive (admin only)

##### [NEW] [analytics.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/api/v1/analytics.py)
- `GET /api/v1/analytics/overview` — Dashboard overview metrics
- `GET /api/v1/analytics/intent-distribution?period=week` — Intent breakdown
- `GET /api/v1/analytics/confidence-over-time` — Confidence trend data
- `GET /api/v1/analytics/feedback-summary` — Approval/edit/reject rates by intent
- `GET /api/v1/analytics/time-saved` — Estimated time saved calculation

##### [MODIFY] [main.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/main.py)
- Mount new routers: `knowledge`, `analytics`

##### [MODIFY] [inference.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/api/v1/inference.py)
- Add `tweet_author` parameter support

---

### Phase 2 — Pipeline Enhancement: Safety Checker + Stage Reorder (Week 2)

This phase adds Stage 5 (Safety Checker) and reorders the pipeline to match v2.0 flow.

---

#### Pipeline

##### [NEW] [safety_checker.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/agent/safety_checker.py)
- `SafetyChecker` class implementing deterministic + LLM-based safety validation:
  - **Deterministic checks**: Block hallucinated URLs (not from approved list), unauthorized promises (timeline/outcome guarantees), medical/legal advice patterns
  - **LLM tone check**: Professional + empathetic verification
  - Returns `SafetyResult(passed: bool, flags: List[str])`

##### [NEW] [safety_keywords.yaml](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/config/safety_keywords.yaml)
- Categorized safety keyword lists: `legal_terms`, `medical_terms`, `promise_patterns`, `approved_urls`

##### [MODIFY] [pipeline.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/agent/pipeline.py)
- Reorder to 5-stage flow: Classify → Escalation Check → RAG Retrieve → Draft → Safety Check
- Add per-stage timing instrumentation (`classification_time_ms`, `retrieval_time_ms`, etc.)
- Skip RAG + Draft stages for escalated tickets (save LLM calls)
- Integrate `SafetyChecker` as final pipeline stage
- Return safety flags in `InferenceResponse`

##### [MODIFY] [retriever.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/agent/retriever.py)
- Add **helpfulness-weighted ranking**: `final_score = (vector_similarity * 0.7) + (helpfulness_ratio * 0.3)`
- Query from `knowledge_base` table instead of (or in addition to) `threads` table
- Add keyword fallback search when vector results are sparse
- Accept `intent_filter` parameter for scoped retrieval

##### [MODIFY] [classifier.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/agent/classifier.py)
- Update `DEFAULT_TAXONOMY` to match v2.0 intent names:

| v1.0 Name | v2.0 Name |
|---|---|
| `iphone_wont_charge` | `charging_issues` |
| `battery_drain` | `battery_performance` |
| `apple_id_account_access` | `apple_id_account` |
| `ios_update_issue` | `ios_update_bugs` |
| `airpods_sound_connectivity` | `connectivity_wifi_bluetooth` |
| `hardware_damage_repair` | `hardware_damage` |
| `billing_and_subscriptions` | `purchase_refund_billing` |
| `icloud_storage_sync` | `icloud_sync_storage` |
| `mac_performance_macos` | `performance_speed` |
| `app_store_downloads` | `app_crashes` |
| `watch_fitness_sync` | `audio_speaker_mic` |
| `other_inquiry` | `display_screen` |

- Update classifier Jinja prompt with new names + descriptions

##### [MODIFY] [escalation.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/agent/escalation.py)
- Update escalation rules to reference new intent names
- Add rules from v2.0 spec: `apple_id_account` + password/hack → ESCALATE, `purchase_refund_billing` + amount > $50 → ESCALATE, Sentiment > 0.85 → ESCALATE PRIORITY

##### [MODIFY] [inference.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/schemas/inference.py)
- Add `SafetyResult` schema: `passed` (bool), `flags` (List[str])
- Add safety fields to `InferenceResponse`: `safety_passed`, `safety_flags`
- Add timing fields to `InferenceMeta`: `classification_ms`, `retrieval_ms`, `drafting_ms`, `safety_ms`, `total_ms`

---

### Phase 3 — Frontend Dashboard Enhancements (Week 3-4)

Enhance the existing React frontend with Analytics, Knowledge Base pages, and improved agent workflow.

---

#### Frontend Pages

##### [NEW] [AnalyticsPage.tsx](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/pages/AnalyticsPage.tsx)
- Overview metrics cards: Tickets Today, AI Approval Rate, Avg Response Time, Escalation Rate, Time Saved
- Intent distribution bar chart (using recharts or custom CSS bars)
- Performance metrics panel: Approval Rate, Avg Edit Distance, Pipeline Latency, Escalation Rate, Est Time Saved, KB Size
- Fetches from `/api/v1/analytics/overview`, `/api/v1/analytics/intent-distribution`, `/api/v1/analytics/feedback-summary`

##### [NEW] [KnowledgeBasePage.tsx](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/pages/KnowledgeBasePage.tsx)
- Searchable/filterable list of knowledge base entries
- Shows source type (seed/agent_approved/manual), intent tag, helpfulness ratio, times retrieved
- Admin can toggle entries active/inactive
- KB stats summary card (total entries, from seed, from feedback, growth %)

##### [MODIFY] [TicketDetailPage.tsx](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/pages/TicketDetailPage.tsx)
- Add safety flags banner (yellow warning panel when `safety_flags.length > 0`)
- Add per-stage timing display (classification, retrieval, drafting, safety check)
- Track `review_time_seconds` on the client (start timer when page loads, submit with feedback)
- Enhanced feedback submission: include `final_response_text`, `review_time_seconds`, `edit_distance_ratio` computed client-side
- Show "Response added to knowledge base ✓" confirmation after approval

##### [MODIFY] [InboxPage.tsx](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/pages/InboxPage.tsx)
- Add `tweet_author` field to "Simulate Incoming Tweet" modal
- Show safety flag badges on ticket cards
- Add `draft_ready` and `pending` status filter options

##### [MODIFY] [AppShell.tsx](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/components/layout/AppShell.tsx)
- Add sidebar navigation items: "📊 Analytics" (`/analytics`), "📚 Knowledge Base" (`/knowledge`)
- Update branding to "Apple Support AI Co-Pilot v2.0"

##### [MODIFY] [router.tsx](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/router.tsx)
- Add routes: `/analytics` → `<AnalyticsPage />`, `/knowledge` → `<KnowledgeBasePage />`

##### [MODIFY] [apiClient.ts](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/services/apiClient.ts)
- Add API methods:
  - `getAnalyticsOverview()`, `getIntentDistribution(period)`, `getFeedbackSummary()`, `getTimeSaved()`
  - `getKnowledgeEntries(intent, page, size)`, `getKnowledgeStats()`, `seedKnowledge()`, `toggleKnowledgeEntry(id, active)`
- Enhance `submitFeedback()` to include `final_response_text`, `review_time_seconds`

##### [MODIFY] [index.ts](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/frontend/src/types/index.ts)
- Add types: `KnowledgeEntry`, `KnowledgeStats`, `AnalyticsOverview`, `IntentDistribution`, `FeedbackSummary`, `TimeSaved`, `SafetyResult`
- Update `InferenceResponse` type with `safety_passed`, `safety_flags`, timing fields

---

### Phase 4 — Golden Test Set & Evaluation Refresh (Week 5)

Update the evaluation framework to match the v2.0 pipeline and new intent taxonomy.

---

##### [NEW] [golden_test_set.json](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/eval/golden_set/golden_test_set.json)
- 50 manually labeled test cases in v2.0 format:
  ```json
  {
    "id": 1,
    "tweet": "...",
    "expected_intent": "battery_performance",
    "min_confidence": 0.80,
    "should_escalate": false,
    "must_contain_in_response": ["battery", "settings"],
    "must_not_contain_in_response": ["sorry for the inconvenience"],
    "difficulty": "easy"
  }
  ```
- Coverage: All 12 v2.0 intents, PII scenarios, safety edge cases, multi-intent tweets, very short/long inputs

##### [NEW] [evaluate_pipeline.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/eval/evaluate_pipeline.py)
- `PipelineEvaluator` class running full v2.0 pipeline against golden test set
- Outputs: intent accuracy, escalation accuracy, safety violation count, avg confidence, avg pipeline time, per-intent accuracy, confusion matrix

##### [MODIFY] [run.py (eval)](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/eval/run.py)
- Update to use new intent names in baseline comparisons
- Add safety violation tracking to evaluation metrics

---

### Phase 5 — Docker & Deployment Polish (Week 6)

---

##### [MODIFY] [docker-compose.yml](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/docker-compose.yml)
- Update environment variables for new services
- Add `REACT_APP_API_URL` to frontend service
- Add GPU reservation for Ollama (with graceful fallback for CPU-only)

##### [MODIFY] [Dockerfile (backend)](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/Dockerfile)
- Add `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"` to pre-download embedding model at build time

##### [MODIFY] [init_db.py](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/backend/app/db/init_db.py)
- Add creation of new tables: `knowledge_base`, `escalation_log`, `analytics_daily`, `system_config`
- Seed default `system_config` entries (escalation thresholds, safety keywords)

---

### Phase 6 — README & Documentation (Week 7)

---

##### [MODIFY] [README.md](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/README.md)
- Complete rewrite following v2.0 template:
  - Hero description with architecture diagram
  - Quick Start (3 commands: clone, docker-compose up, open dashboard)
  - Evaluation results table with real metrics
  - Tech stack grid
  - Project structure tree
  - Key design decisions (Why RAG, Why HITL, Why Deterministic Escalation)
  - Roadmap with checkboxes

##### [MODIFY] [DECISIONS.md](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/DECISIONS.md)
- Add new decisions: Safety Checker rationale, Helpfulness-weighted RAG, Feedback Loop architecture, Analytics time-saved formula

##### [MODIFY] [REPORT.md](file:///c:/D/python/AI-Customer-Suppor-AppleSupport/REPORT.md)
- Update with v2.0 pipeline description, new evaluation metrics, safety checker results

---

## Verification Plan

### Automated Tests

```bash
# Run existing backend tests (should still pass after each phase)
pytest backend/tests -v

# Run new model tests
pytest backend/tests/test_knowledge_model.py -v
pytest backend/tests/test_safety_checker.py -v

# Run v2.0 pipeline evaluation
python -m backend.app.eval.evaluate_pipeline

# Frontend build check
cd frontend && npm run build

# Docker smoke test
docker compose up -d --build
curl http://localhost:8000/api/v1/health
curl http://localhost:5173
```

### Manual Verification
1. Submit a tweet through the dashboard → verify 5-stage pipeline runs with timing data
2. Approve a draft → verify it appears in Knowledge Base page
3. Check Analytics page → verify metrics are populated
4. Submit a tweet with safety keywords → verify safety flags appear
5. Submit a tweet with PII → verify escalation triggers
6. Check Knowledge Base page → verify entries with helpfulness ratios
7. Run golden test evaluation → verify per-intent accuracy report

---

## Execution Order Summary

| Phase | Deliverable | Est. Files Changed | Est. Files New |
|-------|------------|-------------------|---------------|
| 1 | Models + Services + API routes | ~6 | ~7 |
| 2 | Safety Checker + Pipeline reorder + Intent rename | ~6 | ~2 |
| 3 | Frontend pages + enhanced workflow | ~6 | ~2 |
| 4 | Golden test set + evaluation script | ~2 | ~2 |
| 5 | Docker polish + init_db | ~3 | 0 |
| 6 | README + docs | ~3 | 0 |
| **Total** | | **~26** | **~13** |

> [!TIP]
> Each phase is self-contained and testable independently. The project will remain runnable after each phase completion.
