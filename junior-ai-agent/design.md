# System Design & Architecture — Enterprise Support AI Agent

This document explains the technical architecture, control flow, tool schemas, and safety boundaries of the **Junior Enterprise Support AI Agent**.

---

## 1. High-Level Architecture & Control Flow

The system processes incoming employee support queries through a deterministic, layered pipeline:

```
+-----------------------------------------------------------------------------------+
|                                 Employee Request                                  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     FastAPI Layer (main.py: POST /process)                        |
|   • Pydantic validation: 1 <= length <= 2000 chars, non-whitespace                |
|   • Sanitized error handling: Prevents stack trace & secret disclosure            |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                      Safety Layer 1: Prompt Injection Check                       |
|   • Scans for override commands ("ignore all rules", "reveal secrets")            |
|   • Detected? -> Neutralize & refuse immediately (Confidence: 1.0)                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               Safety Layer 2: Sensitive Consequential Action Check                |
|   • Scans for password resets, credential updates, permission escalation          |
|   • Detected? -> Block autonomous execution & create draft ticket for IT Desk     |
|     (Human-in-the-Loop required, Confidence: 0.95)                                |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         Ambiguity & Context Verification                          |
|   • Scans for vague inputs ("It doesn't work", "broken") lacking context          |
|   • Detected? -> Ask targeted clarifying question (Confidence: 0.30)              |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           Intent Classification (agent.py)                        |
|   • Classifies into: knowledge_question | incident | access_issue | other         |
+-----------------------------------------+-----------------------------------------+
                                          |
                    +---------------------+---------------------+
                    |                                           |
                    v                                           v
+---------------------------------------+   +---------------------------------------+
|  Tool: search_policy (tools.py)       |   | Tool: lookup_service_status (tools.py)|
|  • Queries local mock_data.json       |   | • Checks enterprise service telemetry |
|  • Keyword & token matching           |   | • Detects operational vs major outage |
|  • Grounded answer + source tag       |   +-------------------+-------------------+
|  • Sanitizes retrieved untrusted data |                       |
+-------------------+-------------------+                       v
                    |                       +---------------------------------------+
                    |                       | Tool: create_draft_ticket (tools.py)  |
                    |                       | • For outages / incidents             |
                    |                       | • Assigns critical / high priority    |
                    |                       | • Marks draft_pending_review          |
                    +-------------------+   +-------------------+-------------------+
                                        |                       |
                                        +-----------+-----------+
                                                    |
                                                    v
+-----------------------------------------------------------------------------------+
|                            Structured Response Output                             |
|   • category, summary, response, tools_used, confidence, human_review_required     |
|   • source (optional), draft_ticket (optional), decision_reason                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. End-to-End Request Journey in Plain English

Here is what happens when an employee sends: `"The finance dashboard is down."`

1. **Ingestion & Validation (`main.py`):**
   The request reaches the `POST /process` endpoint. Pydantic validates that the string is between 1 and 2,000 characters and is not empty or just spaces.
2. **Safety Screen (`safety.py`):**
   - The agent checks for prompt injection attempts (none found).
   - The agent checks for direct credential tampering (none found).
   - The agent checks for ambiguity (the request mentions a specific system and condition, so it is actionable).
3. **Intent Classification (`agent.py`):**
   The request contains outage keywords (`"down"`), classifying it as an `incident`.
4. **Service Extraction (`agent.py`):**
   The agent identifies the target entity `"finance dashboard"` and resolves it to the service key `finance_dashboard`.
5. **Tool Invocation (`tools.py`):**
   - The agent invokes `lookup_service_status("finance_dashboard")`.
   - The tool inspects `mock_data.json` and discovers `status: "major_outage"` and `critical: true`.
   - Because the system has a major outage and is business-critical, the agent invokes `create_draft_ticket` with priority `"critical"`.
   - The tool returns a simulated ticket object: `{"ticket_id": "DRAFT-4768", "status": "draft_pending_review", ...}`.
6. **Structured Output Assembly:**
   The agent packages the response with `tools_used: ["lookup_service_status", "create_draft_ticket"]`, `confidence: 0.95`, and flags `human_review_required: True` because human engineers must resolve the underlying database outage.

---

## 3. Why Human Review is Mandatory for Sensitive Requests

In enterprise automation, AI agents must adhere to the **Principle of Least Privilege** and implement a **Human-in-the-Loop (HITL)** architecture for consequential actions:

1. **Identity & Authentication Boundaries:**
   An AI chat interface does not prove physical identity or authorization. If an agent could autonomously reset passwords, any user could type *"Reset my colleague's password now"* and hijack accounts.
2. **Preventing Unauthorized Side Effects:**
   Autonomous agents should triage, retrieve, and draft—not commit unilateral changes to production systems without supervisory sign-off.
3. **Auditing and Compliance:**
   Enterprise standards (ISO 27001, SOC 2, NCA ECC in Saudi Arabia) require verified audit trails for access changes. Generating a `draft_ticket` with status `draft_pending_review` ensures proper human verification occurs before credentials change.

---

## 4. Tool Schemas & Input/Output Contracts

### Tool 1: `search_policy(query: str) -> dict`
- **Purpose:** Searches local knowledge documents for company policies.
- **Input Constraints:** Non-empty string, length <= 500 characters.
- **Output Contract:**
  ```json
  {
    "found": true,
    "answer": "Employees may book economy class for flights under 6 hours...",
    "source": "HR-POL-2024-TRAVEL",
    "title": "Corporate Travel Policy"
  }
  ```
- **Safety Boundary:** If no match is found, returns `found: false`. Never fabricates or hallucinates policy rules.

### Tool 2: `lookup_service_status(service: str) -> dict`
- **Purpose:** Queries enterprise telemetry for operational status.
- **Input Constraints:** Non-empty string, length <= 100 characters.
- **Output Contract:**
  ```json
  {
    "found": true,
    "service": "finance_dashboard",
    "status": "major_outage",
    "critical": true,
    "description": "Finance reporting database connection timeout."
  }
  ```
- **Safety Boundary:** If the service is unrecognized, returns `found: false, status: "unknown"`. Refuses to invent operational telemetry.

### Tool 3: `create_draft_ticket(category: str, summary: str, priority: str) -> dict`
- **Purpose:** Simulates draft ticket creation for human agent review.
- **Input Constraints:** Category string, summary string, priority in `["low", "medium", "high", "critical"]`.
- **Output Contract:**
  ```json
  {
    "ticket_id": "DRAFT-4768",
    "status": "draft_pending_review",
    "category": "incident",
    "summary": "Outage on finance_dashboard: Database timeout",
    "priority": "critical",
    "is_simulation": true,
    "message": "Draft ticket created for IT human review. No live external action taken."
  }
  ```
- **Safety Boundary:** Strictly marks `is_simulation: true`. Never performs live API calls to Jira, ServiceNow, or Zendesk.

---

## 5. Confidence Estimation Methodology

Rather than presenting an arbitrary probability number, the agent computes a **documented heuristic confidence score** reflecting evidence quality:

| Scenario | Confidence Score | Rationale |
|----------|:----------------:|-----------|
| **Blocked Prompt Injection** | **1.00** | High certainty in deterministic security rule match. |
| **Confirmed Outage on Known Service** | **0.95** | Telemetry directly confirmed service state from authoritative registry. |
| **Sensitive Action Intercepted** | **0.95** | Explicit security policy matched; high certainty in routing for human review. |
| **Direct Policy Match** | **0.90** | Query matched exact keywords and source document in knowledge base. |
| **Operational Service Guidance** | **0.85** | Verified service is operational; offering standard client-side troubleshooting. |
| **Unknown Service Query** | **0.50** | Telemetry lacked record of requested service; moderate uncertainty. |
| **Policy Not Found** | **0.40** | Knowledge base query returned zero matches; low grounding certainty. |
| **Ambiguous / Vague Query** | **0.30** | Query lacked identifying nouns or context; asking for clarification. |
| **Unsupported / Out-of-Domain** | **0.20** | Query falls entirely outside enterprise support capabilities. |
| **Tool Failure / System Error** | **0.00** | Tool execution crashed or raised exception; zero factual confidence. |

---

## 6. Chain-of-Thought and Privacy Policy

To adhere to enterprise safety best practices:
- **No Hidden Chain-of-Thought Exposed:** The agent does not expose raw intermediate deliberation tokens to users.
- **Observable Decision Reason:** Returns a concise, auditable `decision_reason` explaining the specific policy rule or telemetry signal that guided the action.
- **Untrusted Content Sanitization:** Retrieved documents and user inputs are filtered so malicious prompt-injection payloads are neutralized before output rendering.
