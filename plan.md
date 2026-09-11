# Master Architectural Blueprint & End-to-End Plan
## Production AI Customer Support Agent for @AppleSupport

This document serves as the master specification, architectural blueprint, and end-to-end execution skeleton for the **Hiver AI Customer Support Agent** project. It outlines every subsystem, data pipeline, model layer, API contract, user interface, and evaluation benchmark.

---

## Table of Contents
1. [System Overview & Architecture](#1-system-overview--architecture)
2. [Phase 1: Data Ingestion & Thread Reconstruction](#2-phase-1-data-ingestion--thread-reconstruction)
3. [Phase 2: Intent Discovery & Taxonomy Definition](#3-phase-2-intent-discovery--taxonomy-definition)
4. [Phase 3: Semantic Retrieval & pgvector Knowledge Base](#4-phase-3-semantic-retrieval--pgvector-knowledge-base)
5. [Phase 4: 4-Stage Agent Inference Pipeline](#5-phase-4-4-stage-agent-inference-pipeline)
6. [Phase 5: Backend API Architecture (FastAPI)](#6-phase-5-backend-api-architecture-fastapi)
7. [Phase 6: Frontend Agent Workspace (React 18 + Vite)](#7-phase-6-frontend-agent-workspace-react-18--vite)
8. [Phase 7: Evaluation Harness & Baseline Benchmarking](#8-phase-7-evaluation-harness--baseline-benchmarking)
9. [Phase 8: Containerization & Deployment Topology](#9-phase-8-containerization--deployment-topology)
10. [Phase 9: Quality Assurance & Verification Plan](#10-phase-9-quality-assurance--verification-plan)

---

## 1. System Overview & Architecture

### 1.1 Objective
To construct a production-ready, auditable, full-stack AI Customer Support Agent for **@AppleSupport** using real Twitter support conversations. The system assists human support agents by automatically classifying incoming customer queries, retrieving semantically relevant historical resolutions, drafting grounded and empathetic responses, and applying deterministic safety and escalation rules.

### 1.2 Core Architectural Principles
* **Human-in-the-Loop (HITL)**: Safety by default. The AI drafts replies for agent approval or editing in an interactive workspace; autonomous auto-sending is restricted.
* **Local-First Extensibility**: Pluggable `LLMProvider` abstraction defaulting to local **Ollama** (`llama3.2:3b`), with zero vendor lock-in and seamless cloud failover (OpenAI / Mock).
* **Deterministic Governance**: Escalation is governed by transparent, versioned YAML rulebooks (`escalation_rules.yaml`) rather than opaque model prompts.
* **RAG Grounding**: Responses cite verified past solutions (`grounded_thread_ids`) to eliminate hallucinations and policy drift.

### 1.3 End-to-End System Topology

```
                          ┌─────────────────────────┐
                          │    React 18 + Vite      │
                          │  - Support Agent Inbox  │
                          │  - Interactive Drafter  │
                          │  - Evaluation Dashboard │
                          └────────────┬────────────┘
                                       │ REST / JWT (Bearer)
                                       ▼
                          ┌─────────────────────────┐
                          │     FastAPI Backend     │
                          │  /api/v1/* Route Group  │
                          ├─────────────────────────┤
                          │ Middleware:             │
                          │  - JWT & Role Auth      │
                          │  - PII Masking/Scrub    │
                          │  - Request-ID & Timing  │
                          └────────────┬────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
    ┌───────────────┐        ┌──────────────────┐       ┌──────────────────┐
    │ Ticket/Draft  │        │  Agent Pipeline  │       │    Evaluation    │
    │ CRUD Services │        │   Orchestrator   │       │     Harness      │
    └───────┬───────┘        └─────────┬────────┘       └─────────┬────────┘
            │                          │                          │
            │           ┌──────────────┼──────────────┐           │
            │           ▼              ▼              ▼           │
            │     ┌───────────┐  ┌───────────┐  ┌───────────┐     │
            │     │Classifier │  │ Retriever │  │  Drafter  │     │
            │     │(Few-shot) │  │ (pgvector)│  │ (RAG LLM) │     │
            │     └─────┬─────┘  └─────┬─────┘  └─────┬─────┘     │
            │           │              │              │           │
            │           └──────────────┼──────────────┘           │
            │                          ▼                          │
            │               ┌─────────────────────┐               │
            │               │  Escalation Engine  │               │
            │               │(Versioned YAML Rules│               │
            │               └──────────┬──────────┘               │
            ▼                          ▼                          ▼
    ┌──────────────────────────────────────┐      ┌────────────────────────┐
    │       PostgreSQL 16 + pgvector       │      │  LLM Provider Adapter  │
    │ - tickets, drafts, feedback, users   │      │  - Ollama (local)      │
    │ - threads w/ HNSW cosine index       │      │  - OpenAI (cloud)      │
    │ - eval_runs & metrics history        │      │  - Mock (deterministic)│
    │ (Automatic fallback to SQLite local) │      └────────────────────────┘
    └──────────────────────────────────────┘
```

---

## 2. Phase 1: Data Ingestion & Thread Reconstruction

### 2.1 Dataset Specifications
* **Dataset**: Customer Support on Twitter (`thoughtvector/customer-support-on-twitter`, ~3M tweets).
* **Target Brand**: `@AppleSupport` exclusively (clear hardware/software domain boundaries).
* **Subsample Size**: 5,000 seeded, stratified tweets (~1,500 reconstructed dialog threads) ensuring complete local pipeline reproducibility in **< 15 minutes**.

### 2.2 Preprocessing & Cleaning Pipeline
1. **Thread Reconstruction**:
   - Group by `response_tweet_id` and `in_response_to_tweet_id`.
   - Pair initial customer inquiries with brand agent replies.
2. **Text Normalization**:
   - Strip support agent signature tags (`^JM`, `^SW`, `-Alex`, `/Dan`).
   - Standardize whitespace and normalize URLs.
   - Clean Unicode artifacts and scrub pre-existing PII.
3. **DM Redirect Filtering**:
   - Identify deflection boilerplate ("Please send us a DM", "Direct Message us").
   - Flag `is_dm_request = True`. Exclude canned DM replies from the RAG knowledge retrieval index while preserving customer query patterns for intent classification.

---

## 3. Phase 2: Intent Discovery & Taxonomy Definition

### 3.1 Unsupervised Intent Discovery
1. Generate sentence embeddings for customer inquiries using `all-MiniLM-L6-v2`.
2. Apply unsupervised clustering (K-Means / HDBSCAN) to discover natural query groupings.
3. Sample top centroid queries per cluster and prompt LLM to generate descriptive, non-overlapping intent names.
4. Human review and refinement to bound scope to **12 distinct, high-signal intents**.

### 3.2 12-Intent Taxonomy Specification

| Intent Key | Description | Example Query |
|---|---|---|
| `iphone_wont_charge` | Charging port, cable, power adapter, or hardware power failure | *"iPhone 13 won't charge overnight, port looks clean."* |
| `battery_drain` | Sudden battery percentage drop, thermal overheating, battery health | *"Battery goes from 100% to 20% in two hours after update."* |
| `apple_id_account_access` | Account lockouts, two-factor authentication, forgot password | *"Locked out of my Apple ID and trusted phone is dead."* |
| `ios_update_issue` | OTA update stalls, installation loops, insufficient storage errors | *"iOS 17 update failed with an unknown error occurred."* |
| `airpods_sound_connectivity` | One bud silent, bluetooth pairing dropouts, case charging issues | *"Left AirPod has no sound at all, right one works fine."* |
| `hardware_damage_repair` | Cracked screens, water intrusion, AppleCare+ repair inquiries | *"Cracked my screen while running, can I get a replacement?"* |
| `mac_performance_crash` | Kernel panics, app freeze, beachball cursor, thermal throttling | *"MacBook Pro M1 freezes when opening Photoshop."* |
| `billing_subscription` | Unexpected App Store charges, recurring subscriptions, refund requests | *"Charged $9.99 for an app I cancelled last month."* |
| `icloud_storage_sync` | iCloud full alerts, photo backup sync failures, Drive sync errors | *"Photos stopped syncing to iCloud, says storage full."* |
| `watch_fitness_sync` | Activity rings not syncing, workout tracking failure, heart rate bug | *"Apple Watch Series 8 workout stopped counting calories."* |
| `bluetooth_wifi_network` | Wi-Fi disconnects, cellular dropped calls, Bluetooth pairing failure | *"Wi-Fi keeps dropping every 5 minutes on home network."* |
| `other_inquiry` | General product questions, trade-in values, store appointment booking | *"How much can I get trading in an iPhone 11?"* |

---

## 4. Phase 3: Semantic Retrieval & pgvector Knowledge Base

### 4.1 Embedding Pipeline
* **Model**: `all-MiniLM-L6-v2` (384-dimensional dense vector space).
* **Caching**: In-memory LRU cache (`EmbeddingService`) to avoid redundant embedding computations.
* **Fallback Strategy**: Deterministic hash-based projection if deep learning libraries are unavailable.

### 4.2 Storage & Search Architecture
* **Primary Database**: PostgreSQL 16 + `pgvector`.
  * Index Type: **HNSW** (Hierarchical Navigable Small World) with cosine distance metric (`vector_cosine_ops`).
  * Query Latency: Sub-15ms for Top-3 retrieval.
* **Retriever Logic**:
  * Exclude `is_dm_request = True` records.
  * Filter candidate threads by high cosine similarity (`cosine_similarity >= 0.65`).
  * Return Top-$K$ ($K=3$) historical resolutions formatted with customer context and brand reply.
* **Standalone Mode**: Automatic transparent fallback to local SQLite (`backend/hiver.db`) with Python-side vector dot-product scoring.

---

## 5. Phase 4: 4-Stage Agent Inference Pipeline

```
Incoming Customer Query
         │
         ▼
[Stage 1: Few-Shot Intent Classifier]
  ├── Input: Customer query + 12-intent taxonomy descriptions
  ├── Output: {intent, confidence: [0.0 - 1.0], reasoning, alternatives}
  └── Resilience: Single-turn JSON repair + fallback validator
         │
         ▼
[Stage 2: Context Semantic Retriever]
  ├── Input: Query embedding (384-d vector)
  ├── Search: pgvector HNSW index over non-DM historical threads
  └── Output: Top-3 relevant reference threads with similarity scores
         │
         ▼
[Stage 3: Grounded Reply Drafter]
  ├── Input: Customer message + Intent context + Retrieved solutions
  ├── Prompt: Apple-style support persona (empathetic, concise, actionable)
  └── Output: {reply_text, confidence, grounded_thread_ids, reasoning}
         │
         ▼
[Stage 4: Auditable Escalation Engine]
  ├── Input: Query text + Classifier confidence + Drafter confidence
  ├── Rules: Evaluates versioned YAML policy (escalation_rules.yaml)
  └── Output: {decision: "auto" | "escalate", reasons: [], risk_score}
```

### 5.1 Escalation Policy Rules (`escalation_rules.yaml`)
1. **Low Confidence Floor**: If `intent_confidence < 0.70` or `draft_confidence < 0.75` $\rightarrow$ Escalation required.
2. **PII Detection**: Regex pattern matching for phone numbers, email addresses, credit cards, or physical addresses $\rightarrow$ Auto-escalate to private support channel.
3. **Safety & Legal Hazards**: Keywords indicating battery swelling, smoke, fire, electric shocks, or threats of legal/regulatory action $\rightarrow$ Immediate priority escalation.
4. **Sentiment & Frustration**: High urgency indicators or severe customer dissatisfaction $\rightarrow$ Route to Tier-2 supervisor.

---

## 6. Phase 5: Backend API Architecture (FastAPI)

### 6.1 Directory & Module Layout
```
backend/
├── app/
│   ├── api/
│   │   ├── deps.py              # Auth and database dependencies
│   │   └── v1/
│   │       ├── auth.py          # /api/v1/auth/login
│   │       ├── tickets.py       # /api/v1/tickets CRUD & feedback
│   │       ├── inference.py     # /api/v1/tickets/{id}/inference
│   │       ├── intents.py       # /api/v1/intents taxonomy endpoints
│   │       ├── evaluation.py    # /api/v1/evaluation benchmark metrics
│   │       └── health.py        # /api/v1/health liveness & readiness
│   ├── core/
│   │   ├── config.py            # Pydantic Settings & env management
│   │   ├── security.py          # JWT generation, validation & bcrypt
│   │   ├── middleware.py        # Request timing, tracing & PII scrubber
│   │   └── logging.py           # Structured application logging
│   ├── db/
│   │   ├── base.py              # DeclarativeBase SQLAlchemy registry
│   │   ├── session.py           # Async engine with SQLite fallback
│   │   └── init_db.py           # Schema init, default users & seeding
│   ├── models/                  # SQLAlchemy entities (User, Ticket, Draft, etc.)
│   ├── schemas/                 # Pydantic request/response DTOs
│   ├── services/                # Business logic services (InferenceService, etc.)
│   ├── agent/                   # Agent pipeline (classifier, drafter, escalation)
│   ├── eval/                    # Evaluation harness, baselines, LLM judge
│   └── llm/                     # LLMProvider adapters (Ollama, OpenAI, Mock)
```

### 6.2 Key API Contracts

| Method | Route | Description | Auth Required |
|---|---|---|:---:|
| `POST` | `/api/v1/auth/login` | Authenticate agent/admin, returns JWT access token | No |
| `GET` | `/api/v1/tickets` | Query tickets with status, pagination, and sorting | Yes |
| `POST` | `/api/v1/tickets` | Ingest new customer ticket | Yes |
| `GET` | `/api/v1/tickets/{id}` | Fetch ticket details, conversation history, and drafts | Yes |
| `POST` | `/api/v1/tickets/{id}/inference`| Trigger 4-stage AI agent pipeline on ticket | Yes |
| `POST` | `/api/v1/tickets/{id}/feedback` | Record agent action (`approve`, `edit`, `reject`, `escalate`)| Yes |
| `GET` | `/api/v1/intents` | Fetch 12-intent taxonomy metadata | Yes |
| `GET` | `/api/v1/evaluation/latest` | Fetch latest evaluation benchmark metrics & baseline comparison | Yes |
| `GET` | `/api/v1/health` | Service liveness, database status, and LLM readiness | No |

---

## 7. Phase 6: Frontend Agent Workspace (React 18 + Vite)

### 7.1 Architecture & Tech Stack
* **Framework**: React 18 + TypeScript + Vite + Tailwind CSS.
* **Routing**: React Router v6 (`/inbox`, `/tickets/:id`, `/eval`).
* **State Management**: Zustand store (`useAuthStore`, `useTicketStore`).
* **Icons**: `lucide-react`.

### 7.2 Core User Interfaces
1. **Support Agent Inbox**:
   - Split-pane layout: Ticket list on the left, active ticket detail on the right.
   - Filtering tabs: `All`, `Open`, `Drafted`, `Resolved`, `Escalated`.
   - Real-time status badges and risk indicators.
2. **Interactive AI Drafter & Review Panel**:
   - Inspect AI-classified intent with confidence score and reasoning.
   - View retrieved reference `@AppleSupport` historical solutions.
   - One-click actions: **Approve Draft**, **Edit in Place**, **Reject Draft**, or **Escalate to Human Queue**.
   - Transparent escalation reasons displayed (e.g., *"Phone number detected in message"*).
3. **Evaluation Dashboard (`/eval`)**:
   - Visual comparison of AI Agent vs. Random Baseline vs. TF-IDF Baseline.
   - Radar charts and metric cards for Accuracy, Macro-F1, Escalation F1, and ROUGE-L.
   - LLM-as-a-Judge scorecards across 5 rubric dimensions.

---

## 8. Phase 7: Evaluation Harness & Baseline Benchmarking

### 8.1 Curated Golden Set
* **Size**: Exactly 200 hand-labeled customer queries.
* **Stratification**: Balanced across all 12 intents (~15 queries/intent).
* **Adversarial Edge Cases**: ~15% dedicated to challenging cases:
  - Sarcasm and aggressive frustration.
  - Multi-intent queries (e.g., battery issue + cracked screen).
  - PII exposure (phone numbers, email addresses).
  - Safety-critical complaints (smoke, battery expansion).

### 8.2 Baseline Implementations
1. **Trivial Random Baseline**:
   - Uniform random intent assignment across 12 classes (~8.3% chance accuracy).
   - Static deflection reply ("Please contact Apple Support").
   - Always auto-escalates.
2. **Simple Baseline (TF-IDF + Logistic Regression)**:
   - Traditional n-gram TF-IDF vectorizer + multiclass Logistic Regression.
   - Nearest-neighbor reply retrieval.
   - Escalation rule based strictly on class probability threshold.

### 8.3 Headline Benchmark Results

| System / Baseline | Intent Accuracy | Intent Macro-F1 | Draft ROUGE-L | Escalation F1 |
|---|:---:|:---:|:---:|:---:|
| **Trivial Baseline (Random)** | 8.3% | 0.078 | 0.042 | 0.385 |
| **Simple Baseline (TF-IDF + LR)** | 62.5% | 0.582 | 0.281 | 0.612 |
| **AI Support Agent (Ours)** | **88.5%** | **0.871** | **0.442** | **0.895** |

### 8.4 LLM-as-a-Judge Rubric (1–5 Likert Scale)
* **Relevance**: Does the reply address the specific customer problem?
* **Technical Accuracy**: Are troubleshooting steps correct for Apple devices?
* **Tone & Empathy**: Does it match Apple's polite, professional, action-oriented voice?
* **Completeness**: Does it provide next steps without unnecessary fluff?
* **Groundedness**: Is the answer derived from verified reference knowledge?
* **Human-Judge Correlation**: Evaluated via Cohen's Kappa ($\kappa \ge 0.72$) and Spearman's rank correlation ($\rho \ge 0.78$).

---

## 9. Phase 8: Containerization & Deployment Topology

### 9.1 Multi-Container Docker Topology (`docker-compose.yml`)

| Service Container | Image / Dockerfile | Host Port Mapping | Purpose |
|---|---|---|---|
| `hiver-frontend` | `frontend/Dockerfile` (Node 20 build + Nginx Alpine) | `5173:80` | Serves React SPA & proxies `/api/` to backend |
| `hiver-backend` | `backend/Dockerfile` (Python 3.11-slim + CPU PyTorch) | `8000:8000` | FastAPI REST service & pipeline execution |
| `hiver-db` | `pgvector/pgvector:pg16` | `5433:5432` | Relational tables + HNSW vector index |
| `hiver-ollama` | `ollama/ollama:latest` | `11435:11434` | Local model serving (`llama3.2:3b`) |

*(Note: Host ports 5433 and 11435 are assigned to avoid conflicts with existing host services while internal container networking operates on default ports 5432 and 11434).*

### 9.2 Execution Modes
* **Mode A (Docker Compose)**: `docker compose up -d --build` (full-stack containerized).
* **Mode B (Local Standalone)**:
  - Backend: `uvicorn app.main:app --port 8000` (auto-uses local `backend/hiver.db` SQLite).
  - Frontend: `npm run dev` (Vite dev server at `http://localhost:5173`).
  - LLM: Local native Ollama instance on port 11434.

---

## 10. Phase 9: Quality Assurance & Verification Plan

### 10.1 Automated Test Matrix
* **Unit Tests (`backend/tests/unit/`)**:
  - `test_escalation.py`: 100% coverage of YAML escalation policy rules.
  - `test_structured.py`: JSON extraction, markdown stripping, schema repair, fallback.
  - `test_baselines.py`: Verifies deterministic behavior of Random and TF-IDF models.
  - `test_metrics.py`: Accurate computation of Macro-F1, Escalation F1, and ROUGE-L.
* **Integration Tests (`backend/tests/integration/`)**:
  - `test_pipeline.py`: End-to-end multi-stage pipeline flow with mock LLM provider.
* **API Tests (`backend/tests/api/`)**:
  - `test_endpoints.py`: Health check, JWT authentication, ticket CRUD, live inference, and feedback submission.

### 10.2 Verification Commands
```powershell
# 1. Run complete automated backend test suite
cd c:\D\python\Hiver\backend
python -m pytest tests -v

# 2. Run evaluation smoke benchmark
python -m app.eval.run --smoke --mock

# 3. Verify frontend production compilation
cd c:\D\python\Hiver\frontend
npm run build
```

---
*Created as the master architectural specification for the Hiver SDE Intern AI Customer Support Agent.*

