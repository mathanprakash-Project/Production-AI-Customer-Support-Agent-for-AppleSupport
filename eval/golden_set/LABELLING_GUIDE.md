# Golden Set Labelling Guide

## Purpose and Scope
This document provides instructions for manually labelling the golden set evaluation dataset for the AppleSupport AI Customer Support Agent. The golden set acts as the ground truth for evaluating our agent's performance in intent classification, reply drafting, and escalation decisions.

## How to Label Each Field

### `gold_intent`
- **Definition:** The primary issue or question raised by the customer in their first message.
- **Valid Categories:** `technical_support`, `billing_inquiry`, `account_access`, `feature_request`, `complaint`, `general_inquiry`, `unknown`.
- **Instruction:** Read the customer message and select the most appropriate intent. If multiple apply, choose the most severe or direct one (e.g., if a user is complaining about a technical issue, label as `technical_support`).

### `gold_escalation_decision`
- **Definition:** Whether the customer's issue requires human intervention.
- **Valid Values:** `True` (needs escalation) or `False` (can be handled by AI).
- **Decision Criteria for Escalation:**
  - High severity issues (data loss, security breaches).
  - High emotional distress (explicit profanity, threats of churn).
  - Complex technical issues requiring account-specific actions the AI cannot perform.
  - Legal or PR risks.

### `gold_escalation_reason`
- **Definition:** A brief explanation of why the issue should or should not be escalated.
- **Instruction:** Provide a 1-2 sentence justification aligned with the decision criteria above.

### `gold_reply_quality_notes`
- **Definition:** Qualitative notes on what a perfect reply should include.
- **Instruction:** Note specific facts to mention, tone requirements (e.g., "empathetic apology needed"), and actionable next steps.

## Guidelines for Edge Cases
- **Very Short Messages:** (e.g., "help", "broken") Try to infer intent from context if possible, otherwise label as `general_inquiry` and escalate for clarification.
- **Multiple Intents:** Focus on the intent that blocks the user's primary goal.
- **Unclear Meaning:** If the message is incomprehensible, label intent as `unknown` and escalate.

## Note About Single-Annotator Limitations
Currently, labels are provided by a single annotator. This can introduce subjective bias, particularly in borderline escalation cases or tone notes. To mitigate this, reviewers should rely strictly on the documented decision criteria rather than intuition. Future iterations will involve multi-annotator agreement metrics.
