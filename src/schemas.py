from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    id: str = Field(..., description="Stable requirement ID like R-001")
    text: str
    category: str = "General"
    priority: Literal["Must", "Should", "Could", "Unknown"] = "Unknown"
    deliverable: str = ""
    evidence_needed: str = ""


class ComplianceItem(BaseModel):
    requirement_id: str
    requirement: str
    status: Literal["Compliant", "Partial", "Gap", "Unknown"] = "Unknown"
    evidence: str = ""
    response_strategy: str = ""
    owner: str = ""
    confidence: int = Field(default=50, ge=0, le=100)


class RiskItem(BaseModel):
    risk: str
    severity: Literal["High", "Medium", "Low"] = "Medium"
    why_it_matters: str = ""
    mitigation: str = ""
    bid_impact: Literal["Blocker", "Major", "Minor"] = "Minor"


class TimelineMilestone(BaseModel):
    milestone: str
    duration: str
    outputs: str
    dependencies: str = ""


class AnalysisBundle(BaseModel):
    project_title: str = "RFP Analysis"
    opportunity_summary: str = ""
    bid_recommendation: Literal["Strong Bid", "Bid With Caution", "No Bid", "Needs More Info"] = "Needs More Info"
    bid_score: int = Field(default=50, ge=0, le=100)
    win_themes: list[str] = []
    requirements: list[Requirement] = []
    compliance_matrix: list[ComplianceItem] = []
    risks: list[RiskItem] = []
    clarifying_questions: list[str] = []
    solution_architecture: str = ""
    delivery_plan: list[TimelineMilestone] = []
    pricing_assumptions: list[str] = []
    executive_summary: str = ""
    proposal_draft: str = ""
    reviewer_notes: list[str] = []
    quality_score: int = Field(default=50, ge=0, le=100)
