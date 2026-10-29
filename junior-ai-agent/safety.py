"""
safety.py - Safety Rules, Guardrails, and Untrusted Data Validation

This module provides safety checks for the Enterprise Support AI Agent:
1. Sensitive Action Detection (Human-in-the-Loop requirement)
2. Prompt Injection & Jailbreak Detection (Untrusted Input / Content)
3. Ambiguity & Underspecified Request Detection
4. Tool Argument and Output Validation
5. Sanitization of retrieved content

DESIGN PRINCIPLE:
Enterprise support agents must never autonomously modify credentials, alter permissions,
or execute consequential side-effects without explicit human verification.
All user inputs and retrieved documents are treated as untrusted data.

LIMITATIONS (Documented for Technical Defense):
This rules-based implementation uses heuristic string and keyword pattern matching.
While simple, transparent, and deterministic, keyword filtering cannot detect sophisticated
paraphrasing, leetspeak, semantic evasion, or zero-day jailbreaks. In a production system,
this should be complemented with an LLM guardrail model (e.g. Llama Guard, NeMo Guardrails)
and strict RBAC authorization controls.
"""

import re
from typing import Any, Dict, Tuple


# Known sensitive action triggers that must require human review
SENSITIVE_PATTERNS = [
    r"\breset\b.*\bpassword\b",
    r"\bchange\b.*\bpassword\b",
    r"\bpassword\b.*\breset\b",
    r"\bunlock\b.*\baccount\b",
    r"\bdelete\b.*\baccount\b",
    r"\bgrant\b.*\badmin\b",
    r"\bcreate\b.*\badmin\b",
    r"\badmin(istrator)?\b.*\baccount\b",
    r"\bwithout\b.*\bapproval\b",
    r"\belevat(e|ion)\b.*\b(role|access|permission)\b",
    r"\btransfer\b.*\b(fund|money|salary)\b",
    r"\bmodify\b.*\bpermission\b",
    r"\bcolleague.*password\b"
]

# Prompt injection markers attempting to alter agent behavior or reveal secrets
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous\s+)?(rules|instructions|prompts)",
    r"reveal\s+(all\s+)?(secrets|passwords|tokens|system\s+prompt)",
    r"system\s*override",
    r"disregard\s+(all\s+)?(rules|instructions)",
    r"developer\s+mode",
    r"bypass\s+security",
    r"output\s+admin\s+token",
    r"you\s+are\s+now\s+in\s+unrestricted\s+mode"
]

# Vague or ambiguous expressions lacking actionable context
AMBIGUOUS_EXPRESSIONS = [
    "it doesn't work",
    "it doesnt work",
    "doesn't work",
    "doesnt work",
    "broken",
    "help",
    "not working",
    "issue",
    "system error",
    "fix it",
    "it failed",
    "my issue is urgent",
    "issue is urgent",
    "urgent",
    "urgent issue",
    "it is urgent"
]


def is_sensitive_request(text: str) -> Tuple[bool, str]:
    """
    Evaluates whether the request involves a sensitive, consequential action.

    Sensitive actions include:
    - Password resets (self or colleague)
    - Account deletions or unlocks
    - Privilege / role elevation
    - Financial modifications

    Returns:
        (is_sensitive: bool, reason: str)
    """
    if not text:
        return False, "Empty input."

    normalized = text.lower().strip()
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, normalized):
            return True, "Request involves sensitive credential, account, or permission changes requiring human verification."

    return False, "Request is not flagged as sensitive."


def detect_prompt_injection(text: str) -> Tuple[bool, str]:
    """
    Checks if input text or retrieved data contains malicious instructions
    attempting to override system rules or extract internal secrets.

    Returns:
        (has_injection: bool, reason: str)
    """
    if not text:
        return False, "Empty input."

    normalized = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return True, "Prompt injection pattern detected attempting to override rules or expose secrets."

    return False, "No prompt injection detected."


def is_ambiguous_request(text: str) -> Tuple[bool, str]:
    """
    Checks if a request is too vague to act on safely without guessing.
    Instead of hallucinating intent, the agent should ask a clarifying question.

    Returns:
        (is_ambiguous: bool, reason: str)
    """
    if not text:
        return True, "Request is empty."

    cleaned = text.lower().strip().rstrip(".!?")

    # Short query matching known vague expressions
    if cleaned in AMBIGUOUS_EXPRESSIONS:
        return True, f"Request '{text}' lacks specific service, error message, or context."

    # Very short input (less than 15 chars) without actionable nouns
    if len(cleaned.split()) <= 3 and any(amb in cleaned for amb in AMBIGUOUS_EXPRESSIONS):
        return True, "Request is too brief and lacks identifying details."

    return False, "Request contains sufficient detail for initial classification."


def sanitize_untrusted_content(content: str) -> str:
    """
    Sanitizes retrieved knowledge or user-supplied text before returning it.
    Treats all external / retrieved data as untrusted.

    If malicious prompt injection is detected within retrieved content,
    it neutralizes the command to prevent model jailbreaks.
    """
    if not content:
        return ""

    has_injection, _ = detect_prompt_injection(content)
    if has_injection:
        return "[Security Notice: Retrieved content contained unauthorized override instructions and was neutralized. No internal secrets were accessed.]"

    return content


def validate_tool_arguments(tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validates input arguments before invoking any tool.

    Ensures arguments meet type, length, and enum constraints.
    """
    if tool_name == "search_policy":
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return False, "Query must be a non-empty string."
        if len(query) > 500:
            return False, "Query exceeds maximum allowed length of 500 characters."
        return True, "Valid arguments."

    elif tool_name == "lookup_service_status":
        service = args.get("service")
        if not isinstance(service, str) or not service.strip():
            return False, "Service must be a non-empty string."
        if len(service) > 100:
            return False, "Service name exceeds maximum allowed length of 100 characters."
        return True, "Valid arguments."

    elif tool_name == "create_draft_ticket":
        category = args.get("category")
        summary = args.get("summary")
        priority = args.get("priority", "medium")

        if not isinstance(category, str) or not category.strip():
            return False, "Category must be a non-empty string."
        if not isinstance(summary, str) or not summary.strip():
            return False, "Summary must be a non-empty string."
        if priority not in {"low", "medium", "high", "critical"}:
            return False, f"Priority '{priority}' is invalid. Must be low, medium, high, or critical."
        return True, "Valid arguments."

    return False, f"Unrecognized tool: {tool_name}"


def validate_tool_output(tool_name: str, output: Any) -> Tuple[bool, str]:
    """
    Validates that a tool returned a properly formed dictionary.
    """
    if not isinstance(output, dict):
        return False, f"Tool {tool_name} returned non-dictionary output."

    if tool_name == "search_policy":
        if "found" not in output:
            return False, "Missing 'found' field in search_policy output."
        return True, "Valid output."

    elif tool_name == "lookup_service_status":
        if "found" not in output or "status" not in output:
            return False, "Missing required status fields in lookup_service_status output."
        return True, "Valid output."

    elif tool_name == "create_draft_ticket":
        if "ticket_id" not in output or "status" not in output:
            return False, "Missing ticket_id or status in create_draft_ticket output."
        return True, "Valid output."

    return True, "Valid output."
