# Evaluation Run Summary Report

**Timestamp**: 2026-09-12 02:37:04  
**Dataset Size**: 25 golden examples  
**Models**: Task: `mock-agent-model` (mock) | Judge: `mock-judge-model`

---

## 1. Headline Results vs Baselines

| Model / System | Accuracy | Macro-F1 | ROUGE-L | Escalation F1 |
|---|---|---|---|---|
| **Trivial Baseline (Random)** | 0.160 | 0.075 | 0.048 | 0.387 |
| **Simple Baseline (TF-IDF+LR)** | 0.880 | 0.368 | 0.066 | 0.387 |
| **AI Support Agent (Ours)** | **0.240** | **0.032** | **0.142** | **0.286** |

---

## 2. Human–Judge Agreement Study (50 Items)

| Rubric Dimension | Cohen's $\kappa$ (Quadratic) | Spearman $\rho$ | Human Mean | Judge Mean |
|---|---|---|---|---|
| **Relevance** | 0.500 | 0.550 | 5.0 | 5.0 |
| **Accuracy** | 0.000 | 0.550 | 4.76 | 4.0 |
| **Tone** | 0.500 | 0.550 | 5.0 | 5.0 |
| **Completeness** | 0.000 | 0.550 | 5.0 | 4.0 |
| **Groundedness** | 0.500 | 0.550 | 5.0 | 5.0 |

---

## 3. Latency Percentiles (AI Agent)
- **p50 Latency**: 4.0 ms
- **p95 Latency**: 4.0 ms
- **Mean Latency**: 4.3 ms
