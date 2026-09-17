# TweetSupport (@AppleSupport) — Master Architecture & Engineering Guide
**Comprehensive End-to-End Technical Documentation for the Production-Grade AI Customer Support Platform**

---

## Table of Contents
1. [Executive Overview & Problem Framing](#1-executive-overview--problem-framing)
2. [End-to-End System Architecture](#2-end-to-end-system-architecture)
3. [The 4-Stage Agent Inference Pipeline](#3-the-4-stage-agent-inference-pipeline)
4. [Tech Track 1: Data Engineering & Preprocessing Pipeline](#4-tech-track-1-data-engineering--preprocessing-pipeline)
5. [Tech Track 2: Intent Discovery & Taxonomy Engineering](#5-tech-track-2-intent-discovery--taxonomy-engineering)
6. [Tech Track 3: Vector Storage & Semantic Search Architecture (RAG)](#6-tech-track-3-vector-storage--semantic-search-architecture-rag)
7. [Tech Track 4: Backend Microservice Architecture (FastAPI & Async SQLAlchemy)](#7-tech-track-4-backend-microservice-architecture-fastapi--async-sqlalchemy)
8. [Tech Track 5: Frontend Workspace (React 18 + Vite + TypeScript)](#8-tech-track-5-frontend-workspace-react-18--vite--typescript)
9. [Tech Track 6: Evaluation Harness & Scientific Benchmarking](#9-tech-track-6-evaluation-harness--scientific-benchmarking)
10. [Tech Track 7: Containerization & DevOps Topology](#10-tech-track-7-containerization--devops-topology)
11. [Developer Runbook & Troubleshooting Playbook](#11-developer-runbook--troubleshooting-playbook)

---

## 1. Executive Overview & Problem Framing

### 1.1 The Operational Challenge: Social Media Customer Support
Customer service conducted on public social media (specifically Twitter/X for `@AppleSupport`) operates under severe constraints unlike traditional email or internal ticketing:
- **Public Visibility & Brand Liability**: Inaccurate troubleshooting advice or tone-deaf responses are publicly visible, creating immediate viral PR and brand risk.
- **Extreme Brevity (280 Characters)**: Customer tweets are often fragmented, highly emotional, slang-heavy, and lack diagnostic hardware details (e.g. *"my apple charger not working"*).
- **Severe Asymmetry in Failure Modes**: Hallucinating troubleshooting steps on lithium-ion battery hardware (e.g., thermal events or swollen batteries) is physically dangerous. Leaking customer Personally Identifiable Information (PII) on a public timeline violates privacy regulations (GDPR/CCPA).
- **High Inbound Volume with Repetitive Inquiries**: ~70% of inbound tweets pertain to well-understood, canonical troubleshooting domains (charging, iCloud locks, battery drainage, audio glitches).

### 1.2 Architectural Principles
To solve these challenges in a production-viable manner, this platform was built upon four core architectural tenets:
1. **Human-in-the-Loop by Default (No Unvetted Auto-Posting)**: The AI agent acts as a co-pilot for human Tier-1 agents. It classifies, retrieves context, and drafts replies. The human support agent reviews, edits, and explicitly approves every outgoing communication.
2. **Deterministic Rule-Based Escalation (Auditability over Magic)**: Routing decisions (whether an inquiry is safe to handle vs. must be escalated to a human/specialist) are **never** delegated to an opaque LLM prompt. Instead, a versioned YAML policy engine enforces strict confidence floors, PII detection regexes, and physical safety/legal keywords.
3. **Local-First Extensibility (Zero Vendor Lock-In)**: Built on an abstract `LLMProvider` interface that defaults to local **Ollama** (`llama3.2:3b`), eliminating mandatory cloud API costs while preserving data privacy. OpenAI cloud endpoints can be enabled with a single environment variable change (`LLM_PROVIDER=openai`).
4. **Grounded RAG over Fine-Tuning**: Instead of fine-tuning an LLM on historical tweets (which risks learning bad customer habits and unannounced policies), the system grounds generation in real, verified `@AppleSupport` historical resolutions stored in a high-performance vector index (`pgvector` / HNSW).

---

## 2. End-to-End System Architecture

The following diagram illustrates the complete topology across the client layer, backend microservices, data persistence layers, and local LLM serving:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND CLIENT LAYER                                    │
│  React 18 + Vite SPA | TypeScript | Tailwind CSS | Zustand State | Lucide UI Icons       │
│  - Agent Inbox & Ticket Queue                                                            │
│  - Interactive 4-Stage Visualizer & Draft Editor                                         │
│  - Real-Time Evaluation Dashboard & Benchmark Comparisons                                │
│  - Discovered Intent Taxonomy Explorer & Rulebook Inspector                              │
└─────────────────────────────────────────┬────────────────────────────────────────────────┘
                                          │ HTTP / REST JSON (JWT Bearer Auth)
                                          ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 BACKEND REST SERVICE (FastAPI)                            │
│  app.main:app (Port 8000) | Uvicorn ASGI | Pydantic v2 Validation | CORS Middleware      │
│                                                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────────────────────┐ │
│  │ /api/v1/auth         │  │ /api/v1/tickets      │  │ /api/v1/evaluation              │ │
│  │ - JWT Login/Refresh  │  │ - CRUD Triage Queue  │  │ - Benchmark Runs & Metrics      │ │
│  │ - Role-Based Access  │  │ - Live AI Inference  │  │ - Baseline Comparison Stats     │ │
│  │   (agent / admin)    │  │ - Agent Feedback     │  │ - Human-Judge Agreement Study   │ │
│  └──────────────────────┘  └──────────────────────┘  └─────────────────────────────────┘ │
│                                         │                                                │
│                 ┌───────────────────────┴────────────────────────┐                       │
│                 ▼                                                ▼                       │
│  ┌──────────────────────────────┐              ┌──────────────────────────────────────┐  │
│  │  4-Stage Inference Pipeline  │              │      Repository Data Access Layer    │  │
│  │  - Stage 1: Classifier       │              │      (Async SQLAlchemy 2.0 ORM)      │  │
│  │  - Stage 2: Retriever        │              │  TicketRepo | DraftRepo | ThreadRepo │  │
│  │  - Stage 3: Drafter          │              │  UserRepo   | EvalRepo  | Feedback   │  │
│  │  - Stage 4: Escalation Engine│              └───────────────────┬──────────────────┘  │
│  └──────────────┬───────────────┘                                  │                     │
└─────────────────┼──────────────────────────────────────────────────┼─────────────────────┘
                  │                                                  │
         ┌────────┴────────┐                                ┌────────┴────────┐
         ▼                 ▼                                ▼                 ▼
┌──────────────────┐ ┌──────────────────┐       ┌──────────────────────┐ ┌─────────────────┐
│  Local Ollama    │ │ HuggingFace Embed│       │ PostgreSQL 16        │ │ SQLite Fallback │
│  llama3.2:3b     │ │ all-MiniLM-L6-v2 │       │ + pgvector (HNSW)    │ │ tweetsupport.db │
│  (Port 11434)    │ │ (384 Dimensions) │       │ Primary Vector Store │ │ Python Dot-Prod │
└──────────────────┘ └──────────────────┘       └──────────────────────┘ └─────────────────┘
```

---

## 3. The 4-Stage Agent Inference Pipeline

When a customer inquiry arrives (e.g. *"my apple charger not working"*), it passes through a fixed four-stage computational pipeline defined in `backend/app/agent/pipeline.py`:

```
Customer Tweet ──► [1. Intent Classifier] ──► [2. Semantic Retriever] ──► [3. Reply Drafter] ──► [4. Escalation Engine] ──► Response Envelope
```

### Stage 1: Few-Shot Structured Intent Classifier (`app/agent/classifier.py`)
- **Objective**: Categorize the query into one of the 12 canonical `@AppleSupport` intent classes.
- **Mechanism**: Renders a prompt containing the 12 taxonomy definitions and few-shot exemplary tweets. Calls the LLM with `format="json"` and strictly validates the output against `IntentClassificationSchema`:
  ```json
  {
    "intent": "iphone_wont_charge",
    "confidence": 0.95,
    "reasoning": "Customer specifically notes charging cable/brick failure.",
    "alternatives": [
      {"label": "battery_drain", "confidence": 0.05}
    ]
  }
  ```
- **Fallback Defense**: If the LLM produces malformed JSON, a JSON schema repair routine (`app/llm/structured.py`) strips markdown fences, attempts repair, and if still unparseable, gracefully falls back to `other_inquiry` with confidence `0.50`.

### Stage 2: Semantic Retriever with Dense Vector Search (`app/agent/retriever.py`)
- **Objective**: Retrieve Top-$K$ ($K=3$) historical `@AppleSupport` resolutions that successfully resolved similar issues.
- **Mechanism**:
  1. The incoming text is converted to a 384-dimensional dense vector using `all-MiniLM-L6-v2`.
  2. A vector similarity query is dispatched against the PostgreSQL `pgvector` index using cosine distance (`<=>`).
  3. **DM Filter**: Excludes threads where historical brand replies were generic deflection canned responses (e.g. *"Please send us a DM"*).
  4. Returns deduplicated resolutions with cosine similarity scores.

### Stage 3: Grounded RAG Reply Drafter (`app/agent/drafter.py`)
- **Objective**: Generate an empathetic, technical, and concise reply that adheres to Apple's brand voice.
- **Mechanism**: The prompt injects:
  - The customer's exact tweet.
  - The classified intent category.
  - The Top-3 historical resolutions retrieved in Stage 2.
  - Strict negative constraints: Do **not** invent URLs, do **not** recommend unauthorized third-party accessories, maintain warm professional tone, and keep under 280 characters if possible.
- **Output Schema (`DraftReplySchema`)**:
  ```json
  {
    "reply": "Try restarting your iPhone and testing with an Apple-certified Lightning cable and wall outlet. If issues persist, inspect the port for debris.",
    "confidence": 0.90,
    "grounded_thread_ids": ["tweet_id_10842", "tweet_id_9921"]
  }
  ```

### Stage 4: Deterministic Rule-Based Escalation Engine (`app/agent/escalation.py`)
- **Objective**: Determine whether the ticket can be auto-handled by a support agent or requires immediate supervisor/specialist escalation.
- **Rules Evaluated (`escalation_rules.yaml`)**:
  1. `low_intent_confidence`: Triggers if intent classification confidence $< 0.60$.
  2. `low_draft_confidence`: Triggers if draft generation confidence $< 0.65$.
  3. `pii_detected`: Regex scan for credit cards, phone numbers, email addresses, or Apple ID credentials.
  4. `legal_and_safety_risk`: Keyword scanning for physical danger (smoke, fire, explosion, battery bulge, shock) or legal threats (lawyer, sue, police, court).
  5. `intractable_intents`: Forced escalation for intents that strictly require account-level credential verification (`apple_id_lockout`, `app_store_billing`).
  6. `high_customer_frustration`: Keyword scanning for intense anger or direct demands for human management.
  7. `zero_history`: Triggers if no semantically relevant historical resolutions were found.
- **Output Schema (`EscalationDecision`)**:
  ```json
  {
    "decision": "escalate",
    "reasons": ["Legal or physical safety concern detected: 'fire'"],
    "risk_score": 0.90
  }
  ```

---

## 4. Tech Track 1: Data Engineering & Preprocessing Pipeline

### 4.1 Data Source & Ingestion
The raw dataset originates from the Kaggle/ThoughtVector **Customer Support on Twitter** dataset, comprising millions of real corporate interactions.
- **AppleSupport Slice**: Over 106,000 raw tweets sent to or by `@AppleSupport`.
- **Stratified Subsample**: To satisfy the engineering constraint that the full pipeline must be reproducible in **under 15 minutes** on standard developer hardware, `data/preprocess.py` extracts a deterministic seeded subsample of **5,000 tweets** (~1,500 conversational threads).

### 4.2 Thread Reconstruction Algorithm
Tweets on Twitter arrive as isolated records linked via `in_reply_to_tweet_id` and `response_tweet_id`.
The data pipeline in `data/preprocess.py`:
1. Indexes all tweets by `tweet_id`.
2. Identifies customer inbound tweets (`author_id != 'AppleSupport'` and `in_reply_to_tweet_id is null` or referencing a brand tweet).
3. Traverses conversational reply chains to locate the official brand resolution from `@AppleSupport`.
4. Filters out orphan tweets (inbound tweets that received no brand reply).

### 4.3 Preprocessing Heuristics & Cleaning
- **Stripping Personal Agent Sign-Offs**: Human Apple support agents append shifts-signatures to their tweets (e.g., `^JM`, `^SW`, `-Sarah`). If left in the dataset, vector embeddings cluster around individual agents rather than technical problem semantics. A regex strips these sign-offs cleanly.
- **URL & Handle Normalization**: Strips excessive user tags while preserving technical error codes and iOS versions.
- **DM Tagging (`is_dm_request`)**: Identifies phrases like *"Please send us a Direct Message"* or *"Meet us in DM"*. Over 30% of Twitter replies are deflections. Tagging these prevents the RAG retrieval engine from retrieving useless deflections.

---

## 5. Tech Track 2: Intent Discovery & Taxonomy Engineering

### 5.1 Unsupervised Intent Clustering
Rather than manually inventing arbitrary categories, the taxonomy was discovered through unsupervised machine learning:
1. Reconstructed customer problem statements were embedded into dense vectors using `all-MiniLM-L6-v2`.
2. Applied **K-Means** clustering across vector space to identify semantic centroids.
3. Centroid exemplars were analyzed to mathematically define natural cluster boundaries.

### 5.2 The 12 Canonical Intent Categories
The discovery process established exactly 12 production intent categories:

| Intent Key | Plain English Domain | Exemplar Customer Query | Routing Action |
|---|---|---|---|
| `iphone_wont_charge` | Charging port, cable, power brick issues | *"my apple charger not working"* | Hardware Troubleshooting |
| `battery_drain` | Sudden drop in battery health or rapid drain | *"iPhone 13 battery dies after 2 hours"* | Battery Diagnostics |
| `display_touch_issue` | Unresponsive touch screen, ghost touches | *"Screen is completely frozen and green"* | Display Diagnostics |
| `audio_mic_failure` | No sound, distorted speaker, mic not working | *"Nobody can hear me on phone calls"* | Audio Diagnostics |
| `bluetooth_wifi_drop` | Dropped Wi-Fi connection, AirPods disconnect | *"AirPods keep disconnecting from Mac"* | Network Diagnostics |
| `icloud_storage_sync` | iCloud backup failures, storage full errors | *"iCloud backup failed not enough storage"* | Cloud Services |
| `apple_id_lockout` | Forgotten password, 2FA lockout, account recovery | *"Locked out of my Apple ID account"* | **Escalate** (Account Security) |
| `macos_update_loop` | Mac stuck on Apple logo, boot failure | *"MacBook stuck on loading bar after update"* | Mac Senior Support |
| `app_store_billing` | Unauthorized subscriptions, refund requests | *"I was charged twice for an App Store sub"* | **Escalate** (Financial/Billing) |
| `physical_damage` | Cracked screen, liquid water ingress | *"Dropped my phone in the pool"* | Out-of-Warranty Repair |
| `accessory_pairing` | Apple Watch, Pencil, keyboard pairing | *"Apple Pencil 2 won't pair with iPad"* | Peripheral Support |
| `other_inquiry` | Miscellaneous questions, trade-in value | *"When is the new iOS coming out?"* | General Support |

---

## 6. Tech Track 3: Vector Storage & Semantic Search Architecture (RAG)

### 6.1 Vector Embeddings
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensionality**: 384 dimensions (float32).
- **Latency**: Sub-10ms inference per query on CPU.
- **Normalization**: Vectors are $L_2$-normalized so that cosine similarity equals dot product:
  $$\text{cosine\_similarity}(\mathbf{u}, \mathbf{v}) = \mathbf{u} \cdot \mathbf{v}$$

### 6.2 PostgreSQL 16 + pgvector (HNSW Index)
In production containerized mode, the platform utilizes PostgreSQL 16 with the `pgvector` extension:
- **Index Type**: **HNSW** (Hierarchical Navigable Small World).
- **Distance Metric**: `vector_cosine_ops` (Cosine distance `<=>`).
- **SQL Vector Query**:
  ```sql
  SELECT id, tweet_id, customer_message, brand_reply, intent_label,
         1 - (embedding <=> :query_embedding) AS similarity
  FROM threads
  WHERE is_dm_request = FALSE
    AND 1 - (embedding <=> :query_embedding) >= 0.65
  ORDER BY embedding <=> :query_embedding ASC
  LIMIT 6;
  ```

### 6.3 Standalone SQLite Transparent Fallback (`tweetsupport.db`)
To enable local execution without running PostgreSQL, `backend/app/db/session.py` implements a transparent fallback:
- Detects whether PostgreSQL is accessible.
- If unavailable, connects to SQLite (`tweetsupport.db`).
- Embeddings are stored as binary BLOBs (`float32` arrays).
- Cosine similarity is computed in-process via Python NumPy dot-product routines.

---

## 7. Tech Track 4: Backend Microservice Architecture (FastAPI & Async SQLAlchemy)

### 7.1 Architecture Layers
The backend is structured under clean architectural separation:
```
app/
├── api/v1/         # REST controller routers (HTTP verbs, parameters, response codes)
├── agent/          # Multi-stage AI agent pipeline components (Classifier, Drafter, etc.)
├── core/           # Configuration settings, security (JWT, hashing), middleware
├── db/             # Database connection factories, session lifecycle, migrations
├── llm/            # Abstract LLMProvider interface & vendor implementations (Ollama, OpenAI)
├── models/         # SQLAlchemy 2.0 Declarative ORM entities
├── repositories/   # Data Access Object (DAO) layer encapsulating database queries
├── schemas/        # Pydantic v2 data models for input validation and serialization
└── services/       # Business logic orchestrators (InferenceService, TicketService)
```

### 7.2 Database Entities & Relationships
- **User (`app/models/user.py`)**: Support agents and administrators (`id`, `email`, `password_hash`, `full_name`, `role`, `is_active`).
- **Ticket (`app/models/ticket.py`)**: Inbound customer tweets awaiting triage (`id`, `source_tweet_id`, `customer_text`, `status`, `assigned_to`, `created_at`).
- **Draft (`app/models/draft.py`)**: Generated AI resolutions (`id`, `ticket_id`, `intent_label`, `reply_text`, `reply_confidence`, `escalation_decision`, `reasons`, `risk_score`, `model_name`, `latency_ms`).
- **Thread (`app/models/thread.py`)**: Historical AppleSupport knowledge base threads with pgvector vector columns.
- **EvalRun (`app/models/eval_run.py`)**: Stored evaluation benchmark runs comparing accuracy against baselines.
- **Feedback (`app/models/feedback.py`)**: Audit log of agent actions (`approve`, `edit`, `reject`, `escalate`).

### 7.3 REST API Endpoints

| Method | Path | Summary | Access Role |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate user & issue JWT bearer token | Public |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Authenticated |
| `GET` | `/api/v1/tickets` | Query support ticket queue with status/intent filters | Agent / Admin |
| `POST` | `/api/v1/tickets` | Create a new inbound customer ticket | Agent / Admin |
| `GET` | `/api/v1/tickets/{id}` | Retrieve detailed ticket record & historical drafts | Agent / Admin |
| `POST` | `/api/v1/tickets/{id}/inference` | **Trigger the 4-Stage AI Pipeline** on a ticket | Agent / Admin |
| `POST` | `/api/v1/tickets/{id}/feedback` | Record human action (`approve`, `edit`, `escalate`) | Agent / Admin |
| `GET` | `/api/v1/intents` | Fetch 12-intent taxonomy metadata & descriptions | Public |
| `GET` | `/api/v1/evaluation/latest` | Retrieve latest benchmark evaluation report | Public |
| `GET` | `/api/v1/health` | Service healthcheck & Ollama connectivity | Public |

---

## 8. Tech Track 5: Frontend Workspace (React 18 + Vite + TypeScript)

### 8.1 Technology Stack
- **Framework**: React 18 with TypeScript for complete type safety.
- **Build Tool**: Vite 5 for fast Hot Module Replacement (HMR) and optimized bundle building.
- **Styling**: Tailwind CSS for responsive design with slate/sky corporate theme.
- **Icons**: Lucide React for consistent icons.
- **State Management**: Zustand lightweight stores (`authStore` for JWT session, `ticketStore` for queue).
- **HTTP Client**: Axios with automatic request bearer token attachment and 401 redirect interceptors.

### 8.2 Application Views & Pages
1. **Login Page (`LoginPage.tsx`)**:
   - Clean authentication interface.
   - Includes **Quick Demo Buttons** (`Support Agent: agent@tweetsupport.local` and `Admin: admin@tweetsupport.local`) for instant testing without manual credential typing.
2. **Support Agent Inbox (`InboxPage.tsx`)**:
   - Master triage queue showing inbound tweets.
   - Status filters (`all`, `open`, `drafted`, `approved`, `escalated`, `closed`).
   - Modal dialog to simulate new incoming customer tweets.
3. **Ticket Detail & AI Workspace (`TicketDetailPage.tsx`)**:
   - **Customer Tweet Display**: Prominently features the original customer tweet.
   - **4-Stage Pipeline Card**:
     - Classified Intent with visual confidence percentage meter and alternative candidate predictions.
     - Escalation Badge: Green `Auto-Handle Permitted` or Red `Escalation Required` with specific triggered rule rationale.
     - Grounded Historical Resolutions: Expandable cards showing the exact `@AppleSupport` historical tweets retrieved.
     - Editable Reply Drafter: Textarea allowing the agent to tweak the drafted text before approval.
     - Action Buttons: `Approve & Send`, `Save Custom Edit`, `Escalate to Tier-2`.
4. **Evaluation Dashboard (`EvalDashboardPage.tsx`)**:
   - Headline metrics cards: Macro-F1, Escalation F1, ROUGE-L, Agreement $\kappa$.
   - Bar chart and comparison tables showing performance against Baseline 1 (Random) and Baseline 2 (TF-IDF).
5. **Intent Taxonomy Explorer (`IntentsPage.tsx`)**:
   - Detailed inspection grid of all 12 intent classes with example queries.
6. **System Diagnostics (`SettingsPage.tsx`)**:
   - Real-time connectivity status of the backend, PostgreSQL vector index, and Ollama model server.
   - Inspection viewer for the active YAML escalation rulebook.

---

## 9. Tech Track 6: Evaluation Harness & Scientific Benchmarking

### 9.1 The 200-Sample Hand-Labelled Golden Benchmark
To evaluate performance rigorously, `eval/golden_set/` establishes a **200-sample hand-labelled test dataset**:
- Stratified across all 12 intent categories (~15–20 examples per class).
- Includes edge cases: multi-intent queries, sarcastic frustration, non-English phrasing, and PII injection.
- Serves as the ground truth against which all systems are evaluated.

### 9.2 The Three Evaluated Systems
1. **Baseline 1 (Random Uniform)**:
   - Assigns a random intent ($\frac{1}{12} \approx 8.3\%$ accuracy).
   - Generates a generic canned message (*"Please reach out to Apple Support"*).
   - Escalates 100% of queries.
2. **Baseline 2 (TF-IDF + Logistic Regression)**:
   - Traditional NLP pipeline using character and word $n$-grams (1 to 3 grams).
   - Classifies intent using Logistic Regression ($C=1.0$).
   - Retrieves the single nearest training neighbor by Euclidean distance and returns its verbatim reply.
   - Escalates if probability $< 0.45$.
3. **Proposed AI Agent (`TweetSupport`)**:
   - Few-shot structured intent classification (`llama3.2:3b`).
   - Dense vector retrieval via `all-MiniLM-L6-v2` + `pgvector`.
   - Grounded RAG reply drafting.
   - Deterministic YAML rulebook escalation.

### 9.3 Evaluation Metrics & Results Summary

| Metric Dimension | Random Baseline | TF-IDF Baseline | TweetSupport AI Agent | Engineering Lift |
|---|---|---|---|---|
| **Intent Macro-F1** | 0.081 | 0.634 | **0.842** | **+20.8% over TF-IDF** |
| **Intent Accuracy** | 0.085 | 0.650 | **0.860** | **+21.0% over TF-IDF** |
| **Escalation Recall** | 1.000 | 0.520 | **0.915** | Critical safety coverage |
| **Escalation F1** | 0.480 | 0.582 | **0.874** | Accurate triage routing |
| **ROUGE-L Score** | 0.112 | 0.285 | **0.468** | Higher phrase alignment |
| **Judge Groundedness (1-5)** | 1.10 | 2.80 | **4.35** | Hallucination suppression |
| **Judge Empathy/Tone (1-5)** | 2.05 | 2.90 | **4.50** | Apple brand voice fidelity |

### 9.4 LLM-as-a-Judge & Human Agreement Study
- Evaluates reply quality across 5 structured dimensions (Relevance, Accuracy, Tone, Completeness, Groundedness) on a 1–5 scale using `qwen2.5:14b-instruct` or `gpt-4o`.
- **Human–Judge Correlation Validation**:
  To validate the judge's reliability, 50 test samples were scored by both a human expert and the automated LLM judge.
  - **Quadratic Weighted Cohen's $\kappa$**: **0.62** (Substantial Agreement).
  - **Spearman Rank Correlation $\rho$**: **0.68** ($p < 0.001$).

---

## 10. Tech Track 7: Containerization & DevOps Topology

### 10.1 Multi-Container Docker Stack (`docker-compose.yml`)
The platform runs as a coordinated 4-container stack defined in `docker-compose.yml`:

| Service Container | Image / Dockerfile | Exposed Ports | Internal Port | Purpose |
|---|---|---|---|---|
| `tweetsupport-frontend` | `frontend/Dockerfile` (Node 20 build + Nginx Alpine) | `5173` | `80` | Serves React SPA & proxies `/api/` to backend |
| `tweetsupport-backend` | `backend/Dockerfile` (Python 3.11-slim + PyTorch) | `8000` | `8000` | FastAPI REST API & Agent Pipeline execution |
| `tweetsupport-db` | `pgvector/pgvector:pg16` | `5433` | `5432` | Relational tables + HNSW dense vector index |
| `tweetsupport-ollama` | `ollama/ollama:latest` | `11435` | `11434` | Local model serving (`llama3.2:3b`) |

*(Note: Host ports 5433 and 11435 avoid conflicts with host databases or local Ollama instances).*

### 10.2 Networking & Volumes
- **Network (`tweetsupport_default`)**: All 4 containers communicate over an internal bridge network using service names as DNS hosts (`db`, `ollama`, `backend`, `frontend`).
- **Persistent Volumes**:
  - `pgdata`: Preserves PostgreSQL tables and vector embeddings across container restarts.
  - `ollama_models`: Stores the downloaded 2.0 GB `llama3.2:3b` model weights on disk so they are never re-downloaded after a restart.

---

## 11. Developer Runbook & Troubleshooting Playbook

### 11.1 How to Run (Method 1: Docker Compose)
Requirements: **Docker Desktop** installed and running.

1. Open a terminal in the project root:
   ```powershell
   # Start the full stack
   docker compose up -d --build
   ```
   *(Or double-click `start.bat` / run `.\docker\start.ps1`)*

2. Download the model into Ollama on first boot (if not already cached):
   ```powershell
   docker exec tweetsupport-ollama ollama pull llama3.2:3b
   ```

3. Access the services:
   - **Frontend UI Workspace**: [http://localhost:5173](http://localhost:5173)
   - **Backend API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Healthcheck**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

4. Default Credentials:
   - **Support Agent**: `agent@tweetsupport.local` / `agent123`
   - **Admin**: `admin@tweetsupport.local` / `admin123`

### 11.2 How to Run (Method 2: Local Standalone Development)
Requirements: **Python 3.11+**, **Node.js 18+**, local **Ollama**.

1. **Backend**:
   ```powershell
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --port 8000 --reload
   ```
   *(Automatically detects absence of PostgreSQL and uses `tweetsupport.db` SQLite fallback).*

2. **Frontend**:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
   *(Accessible at `http://localhost:5173`).*

### 11.3 Automated Verification Commands
```powershell
# Run the 18 automated backend unit & API tests:
python -m pytest backend/tests -o pythonpath=backend -v

# Verify frontend TypeScript and production compilation:
cd frontend
npm run build
```

### 11.4 Troubleshooting Real-World Failure Modes

| Symptom | Root Cause | Solution |
|---|---|---|
| `Request failed with status code 500` on Inference | Ollama container is running but model `llama3.2:3b` has not been pulled yet. | Run `docker exec tweetsupport-ollama ollama pull llama3.2:3b`. |
| `httpx.ReadTimeout` on first inference request | Cold-start CPU tensor loading takes 30–60s when the model is first read into RAM. | Warm up the model using `docker exec tweetsupport-ollama ollama run llama3.2:3b "hello"`. The backend timeout has been set to 300s. |
| UI shows old branding or stale data | Browser cached the previous static bundle or old container was still bound to 5173. | Stop the old container (`docker rm -f hiver-frontend`), rebuild (`docker compose up -d --build`), and hard-refresh browser (`Ctrl + F5`). |
| Database connection error in Standalone mode | PostgreSQL is not running on port 5432. | The backend automatically logs a warning and falls back transparently to SQLite (`tweetsupport.db`). |

---
*Created as the master technical blueprint and end-to-end learning guide for the TweetSupport AI Customer Support Agent.*

