"""
main.py - FastAPI Application for Junior Enterprise Support AI Agent

This module exposes the AI Support Agent as an HTTP REST API using FastAPI.

Endpoints:
- GET /: Health check confirming that the service is running.
- POST /process: Processes an employee request and returns a structured response.
- GET /docs: Interactive Swagger UI documentation.

Run locally:
    uvicorn main:app --reload
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

import agent


app = FastAPI(
    title="Junior Enterprise Support AI Agent API",
    description=(
        "Simulated Enterprise Support AI Agent for Apex AI Arabia Technical Assessment. "
        "Provides triage, policy search, service status checks, and safe draft ticketing."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# -------------------------------------------------------------
# Request & Response Schemas (Pydantic)
# -------------------------------------------------------------

class RequestPayload(BaseModel):
    """Schema for incoming employee support requests."""
    request: str = Field(
        ...,
        description="Text describing the employee issue, question, or request.",
        min_length=1,
        max_length=2000,
        examples=["Where is the travel policy?"]
    )

    @field_validator("request")
    @classmethod
    def validate_not_whitespace(cls, value: str) -> str:
        """Rejects empty strings or strings containing only whitespace."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Request cannot be empty or contain only whitespace.")
        return cleaned


class AgentResponse(BaseModel):
    """Structured response schema returned by the agent."""
    category: str = Field(..., description="Classification category (knowledge_question, incident, access_issue, account_action, other)")
    summary: str = Field(..., description="One-line summary of the situation")
    response: str = Field(..., description="Actionable, safe message returned to the employee")
    tools_used: List[str] = Field(..., description="List of mock tools invoked during processing")
    confidence: float = Field(..., description="Documented confidence estimate (0.0 to 1.0)")
    human_review_required: bool = Field(..., description="True if human intervention or review is required")
    source: Optional[str] = Field(None, description="Document source identifier if retrieved from knowledge base")
    draft_ticket: Optional[Dict[str, Any]] = Field(None, description="Draft ticket details if created")
    decision_reason: Optional[str] = Field(None, description="Concise rationale for agent decision")


# -------------------------------------------------------------
# Error Handlers: Prevent leaking stack traces or internal secrets
# -------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Returns clean validation error details without stack traces."""
    errors = [
        {"field": " -> ".join(str(loc) for loc in err.get("loc", [])), "message": err.get("msg")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "The request payload is invalid. Requests must be non-empty and under 2,000 characters.",
            "details": errors
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors and returns a sanitized 500 response."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected server error occurred while processing the request. No stack trace is exposed."
        }
    )


# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------

@app.get("/", summary="Service Health Check")
def health_check() -> Dict[str, str]:
    """
    Root endpoint confirming that the Enterprise Support AI Agent API is running.
    """
    return {
        "status": "online",
        "service": "Enterprise Support AI Agent",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.post("/process", response_model=AgentResponse, summary="Process Employee Request")
def process_endpoint(payload: RequestPayload) -> Dict[str, Any]:
    """
    Receives an employee request, classifies it, runs safety checks, invokes mock tools
    when appropriate, and returns a structured response.
    """
    try:
        result = agent.process_request(payload.request)
        return result
    except Exception as err:
        # Wrap any unexpected agent error safely
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent processing encountered an unexpected internal error."
        ) from err
