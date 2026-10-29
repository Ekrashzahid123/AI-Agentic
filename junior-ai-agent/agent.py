"""
agent.py - Enterprise Support AI Agent Orchestrator

This module implements the core agent logic in `process_request(request)`.

FLOW OF CONTROL:
1. Validate & Normalize Input
2. Check Safety: Block Prompt Injection
3. Check Safety: Intercept Sensitive Actions (Human-in-the-Loop)
4. Check Ambiguity: Ask Clarifying Questions for Underspecified Requests
5. Classify Request: (knowledge_question, access_issue, incident, account_action, other)
6. Tool Selection & Execution:
   - Policy searches use `search_policy`
   - Service outages use `lookup_service_status` and `create_draft_ticket`
7. Grounding & Sanitization: Treat retrieved data as untrusted
8. Return Structured Output Dictionary
"""

import re
from typing import Any, Dict, List, Optional

import safety
import tools


def classify_intent(text: str) -> str:
    """
    Classifies the user's request into one of five categories:
    - knowledge_question: policy, travel, expenses, rules, guidelines
    - incident: outages, system failures, service errors
    - access_issue: permissions, login difficulties, account access
    - account_action: password resets, account modifications
    - other: general greetings, unsupported topics, or vague requests
    """
    normalized = text.lower().strip()

    # 1. Sensitive Account Action check
    is_sensitive, _ = safety.is_sensitive_request(normalized)
    if is_sensitive:
        return "account_action"

    # 2. Incident keywords (outages, crashes, system down, performance issues)
    incident_keywords = [
        "down", "outage", "crashed", "500 error", "offline", "unavailable",
        "broken system", "not working", "running slowly", "slowly", "latency", "degraded"
    ]
    if any(keyword in normalized for keyword in incident_keywords):
        return "incident"

    # 3. Access Issue keywords (permissions, login problems, account access)
    access_keywords = [
        "cannot access", "cant access", "permission denied", "login failed",
        "access request", "access my account", "unable to access", "locked out"
    ]
    if any(keyword in normalized for keyword in access_keywords):
        return "access_issue"

    # 4. Knowledge Question keywords (specific enterprise policies and guidelines)
    knowledge_keywords = [
        "policy", "policies", "guideline", "guidelines", "handbook",
        "per diem", "allowance", "reimbursement", "travel rules", "expense",
        "expenses", "wfh", "remote work", "leave policy", "vacation policy",
        "leave", "apply for leave", "working from home", "business travel"
    ]
    if any(keyword in normalized for keyword in knowledge_keywords):
        return "knowledge_question"

    # Also match queries like "where is [something] policy" or "how to apply for leave"
    if re.search(r"\b(where|how|what)\b.*\b(policy|guideline|document|rule|form|leave|travel)\b", normalized):
        return "knowledge_question"

    # 5. Default fallback
    return "other"


def extract_service_name(text: str) -> Optional[str]:
    """
    Extracts known or mentioned enterprise services from the user's query.
    Returns the normalized service key, or a cleaned entity name if unrecognized.
    """
    normalized = text.lower()

    # Known services map (sorted from longest to shortest phrase for priority matching)
    service_map = {
        "finance dashboard": "finance_dashboard",
        "finance": "finance_dashboard",
        "payroll system": "payroll_system",
        "payroll": "payroll_system",
        "email system": "email_system",
        "email": "email_system",
        "outlook": "email_system",
        "exchange": "email_system",
        "hr portal": "hr_portal",
        "hr": "hr_portal",
        "vpn gateway": "vpn_gateway",
        "vpn": "vpn_gateway"
    }

    for phrase, service_key in service_map.items():
        if phrase in normalized:
            return service_key

    # Attempt to extract candidate service name from patterns like "The X service is not working"
    match = re.search(r"(?:the\s+)?([a-zA-Z0-9_\-]+)(?:\s+service|\s+system|\s+portal|\s+dashboard)?\s+(?:is\s+not\s+working|is\s+down|crashed|offline|is\s+running\s+slowly|running\s+slowly)", normalized)
    if match:
        candidate = match.group(1).strip()
        return service_map.get(candidate, candidate)

    return None


def process_request(request: str) -> Dict[str, Any]:
    """
    Main entry point for processing enterprise employee requests.

    Args:
        request (str): The raw text query from the employee.

    Returns:
        dict: Structured response containing:
            - category: str
            - summary: str
            - response: str
            - tools_used: list of tool names
            - confidence: float (documented estimate)
            - human_review_required: bool
            - source: str (optional, for knowledge responses)
            - draft_ticket: dict (optional, if draft ticket created)
            - decision_reason: str (concise rationale, no hidden CoT)
    """
    # -------------------------------------------------------------
    # Step 1: Input Validation
    # -------------------------------------------------------------
    if not request or not isinstance(request, str) or not request.strip():
        return {
            "category": "other",
            "summary": "Empty request received.",
            "response": "Your request was empty. Please provide a description of the issue or question.",
            "tools_used": [],
            "confidence": 0.0,
            "human_review_required": False,
            "decision_reason": "Rejected empty or whitespace-only input."
        }

    cleaned_request = request.strip()

    # -------------------------------------------------------------
    # Step 2: Safety Check - Prompt Injection / Jailbreak Detection
    # -------------------------------------------------------------
    has_injection, injection_reason = safety.detect_prompt_injection(cleaned_request)
    if has_injection:
        return {
            "category": "other",
            "summary": "Security alert: Prompt injection detected.",
            "response": (
                "I cannot fulfill this request because it contains instructions attempting to "
                "override system policies or reveal internal parameters. If you need enterprise "
                "support, please submit a standard support query."
            ),
            "tools_used": [],
            "confidence": 1.0,  # Confident in defensive security block
            "human_review_required": True,
            "decision_reason": injection_reason
        }

    # -------------------------------------------------------------
    # Step 3: Safety Check - Sensitive / Consequential Actions
    # -------------------------------------------------------------
    is_sensitive, sensitive_reason = safety.is_sensitive_request(cleaned_request)
    if is_sensitive:
        # Sensitive actions (e.g. password resets) must NEVER be executed automatically.
        # Create a draft ticket for human IT review.
        ticket = tools.create_draft_ticket(
            category="account_action",
            summary=f"Sensitive account action requested: {cleaned_request[:80]}",
            priority="medium"
        )
        return {
            "category": "account_action",
            "summary": "Sensitive account action routed for human review.",
            "response": (
                "For security reasons, credential and account modifications cannot be performed "
                f"automatically by the AI assistant. A draft ticket ({ticket['ticket_id']}) has been "
                "routed to the IT Service Desk for human identity verification."
            ),
            "tools_used": ["create_draft_ticket"],
            "confidence": 0.95,
            "human_review_required": True,
            "draft_ticket": ticket,
            "decision_reason": sensitive_reason
        }

    # -------------------------------------------------------------
    # Step 4: Ambiguity Check
    # -------------------------------------------------------------
    is_ambiguous, ambiguous_reason = safety.is_ambiguous_request(cleaned_request)
    if is_ambiguous:
        return {
            "category": "other",
            "summary": "Clarification required for ambiguous request.",
            "response": (
                "Could you please specify which service or application is having an issue, "
                "and describe the error message or symptom you are experiencing?"
            ),
            "tools_used": [],
            "confidence": 0.30,  # Low confidence due to missing context
            "human_review_required": False,
            "decision_reason": ambiguous_reason
        }

    # -------------------------------------------------------------
    # Step 5: Intent Classification
    # -------------------------------------------------------------
    category = classify_intent(cleaned_request)

    # -------------------------------------------------------------
    # Step 6: Tool Execution Based on Category
    # -------------------------------------------------------------

    # Category A: Knowledge Questions (Policies, guidelines)
    if category == "knowledge_question":
        tools_used = ["search_policy"]
        try:
            policy_result = tools.search_policy(cleaned_request)
        except Exception as err:
            return {
                "category": "knowledge_question",
                "summary": "Tool failure during policy lookup.",
                "response": (
                    "A technical error occurred while retrieving policy information. "
                    "Please contact HR directly or try again later."
                ),
                "tools_used": tools_used,
                "confidence": 0.0,
                "human_review_required": True,
                "decision_reason": f"Tool execution failed safely: {str(err)}"
            }

        if policy_result.get("found"):
            # Check retrieved policy for prompt injection before presenting it
            raw_answer = policy_result["answer"]
            sanitized_answer = safety.sanitize_untrusted_content(raw_answer)

            return {
                "category": "knowledge_question",
                "summary": f"Policy retrieved: {policy_result.get('title')}",
                "response": sanitized_answer,
                "tools_used": tools_used,
                "confidence": 0.90,
                "human_review_required": False,
                "source": policy_result.get("source"),
                "decision_reason": f"Direct policy match found under source {policy_result.get('source')}."
            }
        else:
            return {
                "category": "knowledge_question",
                "summary": "Policy not found in knowledge base.",
                "response": (
                    "I could not find a matching company policy in the knowledge base. "
                    "Please check the company intranet portal or contact HR."
                ),
                "tools_used": tools_used,
                "confidence": 0.40,
                "human_review_required": False,
                "source": None,
                "decision_reason": "No policy matched the query keywords; refused to hallucinate policy."
            }

    # Category B: Incidents and Access Issues
    elif category in ("incident", "access_issue"):
        tools_used: List[str] = []
        service_name = extract_service_name(cleaned_request)

        # Special handling for user account access issues without a third-party service
        if category == "access_issue" and (not service_name or "account" in cleaned_request.lower()):
            return {
                "category": "access_issue",
                "summary": "Safe guidance provided for employee account access issue.",
                "response": (
                    "If you cannot access your account, please check that your username and company email "
                    "are spelled correctly and ensure you are connected to the corporate VPN. If your account "
                    "is locked due to repeated incorrect password attempts, please contact the IT Help Desk "
                    "for verified identity unlock. For security reasons, the assistant cannot unilaterally reset credentials."
                ),
                "tools_used": [],
                "confidence": 0.85,
                "human_review_required": False,
                "decision_reason": "Provided safe self-service access guidance without unauthorized credential modification."
            }

        if not service_name:
            # Service was not specified or extracted
            return {
                "category": category,
                "summary": "Service name not identified in incident report.",
                "response": (
                    "Could you clarify which application or service you are referring to? "
                    "For example: 'Finance Dashboard', 'Payroll System', 'Email', 'HR Portal', or 'VPN'."
                ),
                "tools_used": [],
                "confidence": 0.40,
                "human_review_required": False,
                "decision_reason": "Incident detected but target service entity could not be identified."
            }

        tools_used.append("lookup_service_status")
        try:
            status_result = tools.lookup_service_status(service_name)
        except Exception as err:
            return {
                "category": category,
                "summary": "Tool failure during service status check.",
                "response": (
                    "An error occurred while checking service status telemetry. "
                    "Our IT operations team has been notified."
                ),
                "tools_used": tools_used,
                "confidence": 0.0,
                "human_review_required": True,
                "decision_reason": f"Service lookup failed safely: {str(err)}"
            }

        # Check if service is recognized
        if not status_result.get("found"):
            return {
                "category": category,
                "summary": f"Unknown service '{service_name}' queried.",
                "response": (
                    f"The service '{service_name}' is not recognized in our enterprise catalog. "
                    "Please verify the name or contact the IT Helpdesk."
                ),
                "tools_used": tools_used,
                "confidence": 0.50,
                "human_review_required": False,
                "decision_reason": "Service name not found in registry; avoided fabricating status."
            }

        # Service is known; evaluate status
        current_status = status_result.get("status")
        is_critical = status_result.get("critical", False)
        description = status_result.get("description", "")

        if current_status in ("major_outage", "degraded_performance"):
            # Determine ticket priority based on service criticality and outage severity
            priority = "critical" if is_critical and current_status == "major_outage" else "high"

            tools_used.append("create_draft_ticket")
            ticket = tools.create_draft_ticket(
                category="incident",
                summary=f"Outage on {service_name}: {description}",
                priority=priority
            )

            return {
                "category": category,
                "summary": f"Active {current_status} on {service_name}.",
                "response": (
                    f"Service '{service_name}' is currently experiencing a {current_status}. "
                    f"Details: {description} "
                    f"A draft ticket ({ticket['ticket_id']}) has been created with '{priority}' priority "
                    "for the engineering response team."
                ),
                "tools_used": tools_used,
                "confidence": 0.95,
                "human_review_required": True,
                "draft_ticket": ticket,
                "decision_reason": f"Confirmed {current_status} on {service_name}; escalated via draft ticket."
            }
        else:
            # Service is operational
            return {
                "category": category,
                "summary": f"Service {service_name} is operational.",
                "response": (
                    f"Our monitoring telemetry reports that '{service_name}' is currently operational. "
                    "If you are having trouble connecting, please try restarting your browser, "
                    "clearing cache, or verifying your VPN connection."
                ),
                "tools_used": tools_used,
                "confidence": 0.85,
                "human_review_required": False,
                "decision_reason": f"Telemetry shows {service_name} is operating normally; provided troubleshooting tips."
            }

    # Category C: Other / Polite Greetings or Unsupported Requests
    else:
        normalized = cleaned_request.lower().strip()
        greetings = ["hello", "hi", "how are you", "good morning", "good afternoon", "good evening", "hey"]
        if any(g in normalized for g in greetings):
            return {
                "category": "other",
                "summary": "Polite greeting acknowledged.",
                "response": (
                    "Hello! I am your Enterprise Support AI Assistant. I can assist you with company policies, "
                    "IT service health status, and incident reporting. How may I assist you today?"
                ),
                "tools_used": [],
                "confidence": 0.90,
                "human_review_required": False,
                "decision_reason": "Politely acknowledged user greeting."
            }

        return {
            "category": "other",
            "summary": "Unsupported or out-of-scope request.",
            "response": (
                "I am an enterprise IT support assistant designed to assist with IT services, "
                "company policies, and incident reports. I cannot assist with this request."
            ),
            "tools_used": [],
            "confidence": 0.20,
            "human_review_required": False,
            "decision_reason": "Query does not match any enterprise IT support workflows or mock tools."
        }
