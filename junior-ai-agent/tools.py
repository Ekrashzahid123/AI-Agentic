"""
tools.py - Simulated Mock Tools for Enterprise Support Agent

This module provides three deterministic mock tools:
1. search_policy(query): Searches local policy documents from mock_data.json.
2. lookup_service_status(service): Looks up operational status for known enterprise services.
3. create_draft_ticket(category, summary, priority): Generates a simulated draft support ticket.

All tools operate strictly on local mock data. No external network requests,
real databases, or real ticket submissions are performed.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


# Robust path resolution to locate mock_data.json relative to this file
DATA_FILE_PATH = Path(__file__).resolve().parent / "mock_data.json"


def _load_mock_data() -> Dict[str, Any]:
    """Helper function to load the local mock_data.json file."""
    if not DATA_FILE_PATH.exists():
        raise FileNotFoundError(f"Mock data file not found at: {DATA_FILE_PATH}")
    with open(DATA_FILE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def search_policy(query: str) -> Dict[str, Any]:
    """
    Searches local mock policy data for a query match.

    Args:
        query (str): The search query or question from the employee.

    Returns:
        dict: {
            "found": bool,
            "answer": str or None,
            "source": str or None,
            "title": str or None
        }

    Behavior:
        - Never invents or hallucinates a policy if no match is found.
        - Uses case-insensitive keyword and token matching against policy titles and keywords.
    """
    if not query or not isinstance(query, str) or not query.strip():
        return {
            "found": False,
            "answer": None,
            "source": None,
            "title": None,
            "message": "Empty or invalid query provided."
        }

    cleaned_query = query.strip().lower()
    data = _load_mock_data()
    policies = data.get("policies", [])

    # Common English stop words to exclude from keyword scoring
    stop_words = {"a", "an", "the", "in", "on", "at", "for", "to", "is", "it", "of", "and", "or", "what", "where", "how", "can", "do", "i", "my", "our"}

    # Extract clean words from query
    words = re.findall(r"\b[a-zA-Z0-9_-]+\b", cleaned_query)
    query_tokens = set(words) - stop_words

    best_match: Optional[Dict[str, Any]] = None
    best_score = 0

    for policy in policies:
        score = 0
        policy_title = policy.get("title", "").lower()
        policy_keywords = [k.lower().strip() for k in policy.get("keywords", [])]

        # Check full title phrase match
        if policy_title in cleaned_query:
            score += 5

        # Check each keyword
        for kw in policy_keywords:
            # If the exact keyword or keyword phrase is in the query
            if kw in cleaned_query:
                score += 3
            else:
                # Token-level intersection (ignoring stop words)
                kw_tokens = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", kw)) - stop_words
                common = kw_tokens.intersection(query_tokens)
                if common:
                    score += len(common) * 2

        if score > best_score:
            best_score = score
            best_match = policy

    # Require minimum score of 3 (at least one exact keyword or strong token match)
    if best_match and best_score >= 3:
        return {
            "found": True,
            "answer": best_match["answer"],
            "source": best_match["source"],
            "title": best_match["title"]
        }

    return {
        "found": False,
        "answer": None,
        "source": None,
        "title": None,
        "message": "No matching policy found in local knowledge base."
    }


def lookup_service_status(service: str) -> Dict[str, Any]:
    """
    Checks the local mock service status data.

    Args:
        service (str): Name or alias of the service (e.g. 'finance dashboard', 'email').

    Returns:
        dict: {
            "found": bool,
            "service": str,
            "status": str ("operational" | "degraded_performance" | "major_outage" | "unknown"),
            "critical": bool,
            "description": str
        }

    Behavior:
        - Returns actual status if recognized.
        - Clearly reports unknown service if not in registry. Never invents status.
    """
    if not service or not isinstance(service, str) or not service.strip():
        return {
            "found": False,
            "service": service or "",
            "status": "unknown",
            "critical": False,
            "description": "No service name provided."
        }

    normalized = service.strip().lower().replace(" ", "_").replace("-", "_")
    data = _load_mock_data()
    services = data.get("services", {})

    # Map common aliases to registry keys
    alias_map = {
        "finance": "finance_dashboard",
        "finance_dashboard": "finance_dashboard",
        "finance_system": "finance_dashboard",
        "email": "email_system",
        "email_system": "email_system",
        "exchange": "email_system",
        "outlook": "email_system",
        "hr": "hr_portal",
        "hr_portal": "hr_portal",
        "portal": "hr_portal",
        "vpn": "vpn_gateway",
        "vpn_gateway": "vpn_gateway",
        "payroll": "payroll_system",
        "payroll_system": "payroll_system"
    }

    resolved_key = alias_map.get(normalized, normalized)

    if resolved_key in services:
        entry = services[resolved_key]
        return {
            "found": True,
            "service": resolved_key,
            "status": entry.get("status", "unknown"),
            "critical": entry.get("critical", False),
            "description": entry.get("description", "No description available.")
        }

    return {
        "found": False,
        "service": service.strip(),
        "status": "unknown",
        "critical": False,
        "description": f"Service '{service.strip()}' is not recognized in the enterprise service registry."
    }


def create_draft_ticket(category: str, summary: str, priority: str = "medium") -> Dict[str, Any]:
    """
    Creates a simulated draft ticket for human review.

    Args:
        category (str): Ticket category (e.g. 'incident', 'access_issue', 'account_action').
        summary (str): Brief summary of the issue or request.
        priority (str): Ticket priority ('low', 'medium', 'high', 'critical'). Defaults to 'medium'.

    Returns:
        dict: Details of the simulated draft ticket.

    Behavior:
        - Never submits real tickets to external systems (Jira, ServiceNow, Zendesk).
        - Generates a deterministic mock ID and sets status to 'draft_pending_review'.
    """
    valid_priorities = {"low", "medium", "high", "critical"}
    validated_priority = priority.lower() if priority and priority.lower() in valid_priorities else "medium"

    # Deterministic mock ticket ID based on content length and category
    content_hash = abs(hash(f"{category}:{summary}:{validated_priority}")) % 10000
    mock_id = f"DRAFT-{content_hash:04d}"

    return {
        "ticket_id": mock_id,
        "status": "draft_pending_review",
        "category": category,
        "summary": summary.strip() if summary else "No summary provided",
        "priority": validated_priority,
        "is_simulation": True,
        "message": "Draft ticket created for IT human review. No live external action taken."
    }
