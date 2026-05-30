from __future__ import annotations

import json
import re
from typing import Any

from .llm_clients import LLMGateway, LLMError
from .utils import extract_json

SYSTEM = """You are a senior proposal strategist and AI delivery architect.
You create truthful, evidence-aware RFP analysis for technology services bids.
Never invent client requirements. If a detail is not present, mark it unknown or ask a clarifying question.
Return valid JSON only when requested. Avoid mentioning LLM providers, model names, or internal implementation details."""


def _compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


class BidAgents:
    def __init__(self, llm: LLMGateway | None = None):
        self.llm = llm or LLMGateway()

    def intake_requirements(self, rfp_text: str, company_profile: str, depth: str) -> dict[str, Any]:
        prompt = f"""
Analyze this opportunity like a bid manager.

Return JSON with exactly these keys:
project_title: string
opportunity_summary: string
bid_recommendation: one of ["Strong Bid", "Bid With Caution", "No Bid", "Needs More Info"]
bid_score: integer 0-100
win_themes: array of 4-8 strings
requirements: array of objects with id, text, category, priority, deliverable, evidence_needed

Depth: {depth}
Company/profile/capabilities:
{company_profile or 'No company profile was provided. Infer only generic fit and mark missing capability evidence.'}

RFP / brief text:
{rfp_text}
"""
        return self._json(prompt)

    def compliance_and_risks(self, rfp_text: str, company_profile: str, requirements: list[dict], evidence_pack: dict[str, list[dict]], depth: str) -> dict[str, Any]:
        prompt = f"""
Create a compliance matrix, risk register, and clarifying questions.

Return JSON with exactly these keys:
compliance_matrix: array of objects with requirement_id, requirement, status, evidence, response_strategy, owner, confidence
risks: array of objects with risk, severity, why_it_matters, mitigation, bid_impact
clarifying_questions: array of strings

Rules:
- status must be Compliant, Partial, Gap, or Unknown.
- Use supplied evidence pack; do not fabricate proof.
- For gaps, propose a practical mitigation or partner/subcontract approach.
- Include hidden risks: deadlines, integrations, data access, compliance, acceptance criteria, scope ambiguity, payment dependencies.

Depth: {depth}
Company/profile/capabilities:
{company_profile or 'No company profile was provided.'}

Extracted requirements:
{_compact_json(requirements)}

Evidence pack:
{_compact_json(evidence_pack)}

Original RFP text for context:
{rfp_text[:50000]}
"""
        return self._json(prompt)

    def architecture_and_delivery(self, rfp_text: str, company_profile: str, analysis_so_far: dict, depth: str) -> dict[str, Any]:
        prompt = f"""
You are the solution architect for a proposal response.

Return JSON with exactly these keys:
solution_architecture: string, detailed but concise, with components, data flow, security/governance, and assumptions
delivery_plan: array of objects with milestone, duration, outputs, dependencies
pricing_assumptions: array of strings

Make this useful for an AI/ML, automation, RAG, or software consulting proposal. If the RFP is not technical, adapt to the closest service delivery plan.
Do not put exact prices unless the RFP provides a budget. Give pricing assumptions and effort drivers instead.

Depth: {depth}
Company/profile/capabilities:
{company_profile or 'No company profile was provided.'}

Analysis so far:
{_compact_json(analysis_so_far)}

RFP text:
{rfp_text[:45000]}
"""
        return self._json(prompt)

    def proposal_writer(self, rfp_text: str, company_profile: str, bundle: dict, tone: str) -> dict[str, Any]:
        prompt = f"""
Write a polished client-ready proposal draft from the analysis.

Return JSON with exactly these keys:
executive_summary: string
proposal_draft: string in markdown

Proposal structure:
# Proposal: [Project]
## Understanding of Requirements
## Proposed Solution
## Delivery Plan
## Compliance and Assumptions
## Key Risks and Mitigations
## Questions Before Final Scope
## Why This Team
## Next Steps

Tone: {tone}
Rules:
- Do not sound generic.
- Do not overclaim.
- Tie proposal points to the actual RFP requirements.
- Do not mention LLM providers or backend choices.

Company/profile/capabilities:
{company_profile or 'No company profile was provided. Keep Why This Team generic and honest.'}

Analysis bundle:
{_compact_json(bundle)}

RFP text:
{rfp_text[:35000]}
"""
        return self._json(prompt)

    def reviewer(self, bundle: dict, rfp_text: str) -> dict[str, Any]:
        prompt = f"""
Act as a strict proposal quality reviewer.

Return JSON with exactly these keys:
reviewer_notes: array of 5-10 strings
quality_score: integer 0-100

Review against:
- requirement coverage
- compliance traceability
- clarity of proposal
- missing assumptions
- risk handling
- whether the proposal is specific enough to win
- whether any claims are unsupported

Bundle:
{_compact_json(bundle)}

RFP text:
{rfp_text[:25000]}
"""
        return self._json(prompt)

    def _json(self, prompt: str) -> dict[str, Any]:
        result = self.llm.generate(prompt, system=SYSTEM, json_mode=True)
        return extract_json(result.text)


def heuristic_requirements(text: str, company_profile: str = "") -> dict[str, Any]:
    """Offline fallback so the app can still demo without API keys."""
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if len(x) > 35]
    keyword_re = re.compile(r"\b(must|shall|required|requirement|scope|deliverable|timeline|security|integration|api|dashboard|report|support|deadline|budget|compliance|data|documentation)\b", re.I)
    candidates = [x for x in lines if keyword_re.search(x)] or lines[:20]
    reqs = []
    for i, line in enumerate(candidates[:18], start=1):
        priority = "Must" if re.search(r"\b(must|shall|required)\b", line, re.I) else "Should"
        category = "Security/Compliance" if re.search(r"security|privacy|compliance|audit", line, re.I) else "Delivery"
        if re.search(r"api|integration|dashboard|data|model|automation|rag|agent", line, re.I):
            category = "Technical"
        reqs.append({
            "id": f"R-{i:03d}",
            "text": line[:500],
            "category": category,
            "priority": priority,
            "deliverable": "To be confirmed from final scope",
            "evidence_needed": "Past similar work, architecture approach, timeline, and acceptance criteria",
        })
    return {
        "project_title": "RFP / Proposal Opportunity",
        "opportunity_summary": "Offline heuristic analysis created from requirement-like lines in the uploaded brief. Add API keys for full strategic analysis.",
        "bid_recommendation": "Needs More Info",
        "bid_score": 58,
        "win_themes": [
            "Evidence-backed proposal instead of generic AI drafting",
            "Clear scope extraction and risk control",
            "Practical milestone-based delivery",
            "Human approval before final submission",
        ],
        "requirements": reqs,
    }
