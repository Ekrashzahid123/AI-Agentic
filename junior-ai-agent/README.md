# Junior Enterprise Support AI Agent — Apex AI Arabia Technical Assessment

A simulated enterprise support AI agent built in Python and FastAPI. It receives employee requests, classifies intent, validates safety boundaries, uses mock tools, and returns structured responses with human-in-the-loop escalation.

---

## 1. Project Objective

In enterprise IT and HR environments, automated assistants must triage incoming employee requests reliably. However, AI assistants must never perform unauthorized actions (such as resetting credentials or modifying access rights) without human oversight, nor should they invent facts when data is missing.

This project demonstrates:
1. **Deterministic, Rules-Based Tool Orchestration:** Reliable categorization and tool execution without unpredictable LLM hallucinations or external API fees.
2. **Safety & Human-in-the-Loop Guardrails:** Automatic escalation for sensitive actions (e.g., password resets) and neutralization of prompt-injection attempts.
3. **Structured & Auditable Responses:** Predictable JSON outputs including categories, summaries, tool traces, confidence scores, and sources.
4. **Resilient Failure Handling:** Graceful degradation when mock tools fail or when requested services are unknown.

---

## 2. Technology Stack

- **Language:** Python 3.12+ (standard library: `re`, `json`, `pathlib`)
- **API Framework:** [FastAPI](https://fastapi.tiangolo.com/) (high-performance asynchronous REST API)
- **Data Validation:** [Pydantic v2](https://docs.pydantic.dev/) (input payload bounds and output schema enforcement)
- **ASGI Web Server:** [Uvicorn](https://www.uvicorn.org/) (local development server)
- **Testing Framework:** [pytest](https://docs.pytest.org/) & `TestClient` via [httpx](https://www.python-httpx.org/)
- **Data Storage:** Local JSON fixture (`mock_data.json`)

> **Note on Architecture:** This is a **rules-based, deterministic AI agent**, not a generative LLM wrapper. It avoids third-party dependencies such as LangChain, CrewAI, or paid OpenAI/Anthropic APIs to ensure 100% offline reproducibility, easy defense, and clear logic flow.

---

## 3. Project Structure & Purpose of Every File

```text
junior-ai-agent/
│
├── main.py             # FastAPI entry point: handles endpoints, validation, and HTTP errors
├── agent.py            # Agent orchestrator: classifies intent, routes tools, and shapes output
├── tools.py            # Mock tools: search_policy, lookup_service_status, create_draft_ticket
├── safety.py           # Guardrails: prompt injection checks, sensitive action filters, sanitization
├── mock_data.json      # Local fixture containing enterprise policies and service statuses
├── requirements.txt    # Minimal, pinned Python dependencies
├── README.md           # Beginner-friendly guide and operational documentation
├── design.md           # Architecture flow diagrams, tool contracts, and design rationale
├── evaluation.md       # 13-case test matrix, actual pytest run output, and limitations
├── .gitignore          # Excludes caches, virtual environments, and temporary files
│
└── tests/
    ├── __init__.py     # Marks tests directory as a Python package
    └── test_agent.py   # 13 automated pytest tests covering all assessment requirements
```

### Purpose of Each File:
- **`main.py`**: Runs the web server. It validates incoming JSON payloads using Pydantic, calls the agent, and prevents stack traces or internal secrets from leaking in HTTP responses.
- **`agent.py`**: The "brain" of the agent. It coordinates input normalization, security checks, intent classification, tool invocation, and confidence estimation.
- **`tools.py`**: Implements the mock tools. Queries `mock_data.json` for policies or service health, and creates simulated draft tickets.
- **`safety.py`**: Enforces security boundaries. Detects prompt injections, blocks automated credential modifications, and sanitizes untrusted retrieved data.
- **`mock_data.json`**: A local database representing enterprise knowledge (travel policies, expense guidelines, IT service health).
- **`tests/test_agent.py`**: Pytest test suite asserting that the agent meets all 10 core requirements (plus API edge cases) without failures.
- **`design.md`**: Explains the technical design, control flow, tool contracts, and the necessity of human review.
- **`evaluation.md`**: Full evaluation report detailing test inputs, expected behavior, actual results, and practical next steps.

---

## 4. Setup Instructions for Windows

### Step 1: Open PowerShell or Command Prompt
Navigate to the project directory:
```powershell
cd "c:\Users\Microsoft\Desktop\AI Agentic\junior-ai-agent"
```

### Step 2: (Optional) Create and Activate a Virtual Environment
```powershell
# Create a virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once).*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

---

## 5. How to Run the API and View Swagger UI

### Start the API Server:
From inside the `junior-ai-agent` directory, execute:
```powershell
uvicorn main:app --reload
```

The output will confirm:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Application startup complete.
```

### Open Swagger UI:
Open your browser and navigate to:
**[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

You will see the interactive OpenAPI documentation where you can test `GET /` and `POST /process` directly in your browser.

---

## 6. Example API Requests and Responses

### Example 1: Knowledge Policy Query
**Request (PowerShell):**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/process" -Method Post -ContentType "application/json" -Body '{"request": "Where is the travel policy?"}' | ConvertTo-Json -Depth 4
```

**Response:**
```json
{
  "category": "knowledge_question",
  "summary": "Policy retrieved: Corporate Travel Policy",
  "response": "Employees may book economy class for flights under 6 hours and business class for flights over 6 hours. Daily meal per diem is $75. All travel requires manager pre-approval.",
  "tools_used": [
    "search_policy"
  ],
  "confidence": 0.9,
  "human_review_required": false,
  "source": "HR-POL-2024-TRAVEL",
  "draft_ticket": null,
  "decision_reason": "Direct policy match found under source HR-POL-2024-TRAVEL."
}
```

---

### Example 2: Active Service Incident
**Request (cURL):**
```bash
curl -X POST "http://127.0.0.1:8000/process" -H "Content-Type: application/json" -d "{\"request\": \"The finance dashboard is down.\"}"
```

**Response:**
```json
{
  "category": "incident",
  "summary": "Active major_outage on finance_dashboard.",
  "response": "Service 'finance_dashboard' is currently experiencing a major_outage. Details: Finance reporting database connection timeout. Users cannot generate invoices or view ledger. A draft ticket (DRAFT-4768) has been created with 'critical' priority for the engineering response team.",
  "tools_used": [
    "lookup_service_status",
    "create_draft_ticket"
  ],
  "confidence": 0.95,
  "human_review_required": true,
  "draft_ticket": {
    "ticket_id": "DRAFT-4768",
    "status": "draft_pending_review",
    "category": "incident",
    "summary": "Outage on finance_dashboard: Finance reporting database connection timeout. Users cannot generate invoices or view ledger.",
    "priority": "critical",
    "is_simulation": true,
    "message": "Draft ticket created for IT human review. No live external action taken."
  },
  "decision_reason": "Confirmed major_outage on finance_dashboard; escalated via draft ticket."
}
```

---

### Example 3: Sensitive Action Request (Blocked & Routed)
**Request:**
```json
{
  "request": "Reset my colleague's password now."
}
```

**Response:**
```json
{
  "category": "account_action",
  "summary": "Sensitive account action routed for human review.",
  "response": "For security reasons, credential and account modifications cannot be performed automatically by the AI assistant. A draft ticket (DRAFT-3844) has been routed to the IT Service Desk for human identity verification.",
  "tools_used": [
    "create_draft_ticket"
  ],
  "confidence": 0.95,
  "human_review_required": true,
  "draft_ticket": {
    "ticket_id": "DRAFT-3844",
    "status": "draft_pending_review",
    "category": "account_action",
    "summary": "Sensitive account action requested: Reset my colleague's password now.",
    "priority": "medium",
    "is_simulation": true,
    "message": "Draft ticket created for IT human review. No live external action taken."
  },
  "decision_reason": "Request involves sensitive credential, account, or permission changes requiring human verification."
}
```

---

### Example 4: Ambiguous Request (Clarification Asked)
**Request:**
```json
{
  "request": "It doesn't work."
}
```

**Response:**
```json
{
  "category": "other",
  "summary": "Clarification required for ambiguous request.",
  "response": "Could you please specify which service or application is having an issue, and describe the error message or symptom you are experiencing?",
  "tools_used": [],
  "confidence": 0.3,
  "human_review_required": false,
  "draft_ticket": null,
  "decision_reason": "Request 'It doesn't work.' lacks specific service, error message, or context."
}
```

---

## 7. How to Run Automated Tests

To execute the test suite, run:
```powershell
pytest -v
```

Expected output:
```text
tests/test_agent.py::test_travel_policy_lookup PASSED                    [  7%]
tests/test_agent.py::test_service_incident PASSED                        [ 15%]
tests/test_agent.py::test_ambiguous_request PASSED                       [ 23%]
tests/test_agent.py::test_sensitive_password_reset PASSED                [ 30%]
tests/test_agent.py::test_mock_tool_failure PASSED                       [ 38%]
tests/test_agent.py::test_prompt_injection_in_retrieved_data PASSED      [ 46%]
tests/test_agent.py::test_direct_prompt_injection_in_user_input PASSED   [ 53%]
tests/test_agent.py::test_unsupported_request PASSED                     [ 61%]
tests/test_agent.py::test_business_critical_priority_handling PASSED     [ 69%]
tests/test_agent.py::test_unknown_service PASSED                         [ 76%]
tests/test_agent.py::test_api_empty_and_whitespace_request PASSED        [ 84%]
tests/test_agent.py::test_api_excessive_length_validation PASSED         [ 92%]
tests/test_agent.py::test_api_health_endpoint PASSED                     [100%]

============================= 13 passed in 0.44s ==============================
```

---

## 8. Explanation of the Mock Tools

1. **`search_policy(query)`**:
   - Queries `mock_data.json` using word-level token overlap and keyword matching.
   - Filters out English stop words to eliminate false-positive substring matches.
   - Cites the authoritative document source (e.g. `HR-POL-2024-TRAVEL`).
   - If no match reaches the confidence threshold, it reports no match without inventing rules.
2. **`lookup_service_status(service)`**:
   - Maps normalized service names and aliases to registry keys.
   - Returns real mock status (`operational`, `degraded_performance`, `major_outage`).
   - Clearly flags unrecognized systems as `unknown`.
3. **`create_draft_ticket(category, summary, priority)`**:
   - Generates a simulated ticket with ID format `DRAFT-XXXX` and status `draft_pending_review`.
   - Explicitly returns `is_simulation: True` to ensure no live Jira or ServiceNow APIs are touched.

---

## 9. Safety Boundaries & Security Rules

- **Zero Autonomous Credential Modifications:** The agent refuses to reset passwords or elevate permissions for anyone, routing requests to human IT agents.
- **Prompt Injection Defense:** Scans both user inputs and retrieved knowledge content for jailbreak patterns (`ignore all rules`, `system override`, `reveal secrets`). Neutralizes malicious instructions before answering.
- **Untrusted Data Isolation:** All retrieved content is treated as untrusted strings rather than executable system instructions.
- **No Hidden Chain-of-Thought (CoT):** Returns concise, auditable decision reasons rather than internal raw reasoning tokens.
- **Input Bounds:** Rejects payloads longer than 2,000 characters or containing only whitespace.

---

## 10. What is Real vs. What is Simulated

| Component | Status | Implementation Details |
|-----------|:------:|------------------------|
| **HTTP REST API** | **REAL** | Fully functional FastAPI server with live OpenAPI / Swagger docs at `/docs`. |
| **Request Validation** | **REAL** | Pydantic v2 schemas validating input strings, lengths, and JSON format. |
| **Automated Tests** | **REAL** | 13 live Pytest unit and integration tests executing against the application. |
| **Agent Logic** | **DETERMINISTIC / REAL** | Python orchestration pipeline enforcing classification, safety, and tool contracts. |
| **Enterprise Policies** | **SIMULATED** | Fictional company policies stored locally in `mock_data.json`. |
| **Service Telemetry** | **SIMULATED** | Fictional health states stored locally in `mock_data.json`. |
| **Ticketing System** | **SIMULATED** | Draft ticket dictionary with `is_simulation: True`; no external network calls. |

---

## 11. Known Limitations

1. **Keyword Heuristics:** Currently relies on keyword overlap and regular expressions. Does not understand complex semantic paraphrasing or Arabic queries.
2. **Static Mock State:** Telemetry and tickets are held in local JSON and memory; tickets do not persist across restarts.
3. **Regex Safety Checks:** Heuristic filters can be bypassed by advanced adversarial techniques (such as Base64 encoding or cipher prompts) in the absence of an enterprise LLM guardrail model.

---

## 12. AI-Assistance Disclosure Template

> **Candidate Disclosure Note:**
> *"During the development of this assessment, I utilized AI coding assistance (Antigravity by Google DeepMind) for architectural scaffolding, mock fixture generation, and test case structuring. I personally reviewed, refined, and validated all logic in `agent.py`, `tools.py`, and `safety.py`, verified the 13 automated tests locally using `pytest`, and confirmed that all safety boundaries and mock constraints are strictly upheld."*
