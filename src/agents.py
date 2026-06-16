from __future__ import annotations

import json
import re
import time
from typing import Any, Optional
from datetime import datetime

from .llm_clients import LLMGateway, LLMResult
from .utils import extract_json
from .database import execute_query

SYSTEM_PROMPT = """You are a senior proposal strategist, capture manager, and AI delivery architect.
You create detailed, evidence-aware analyses for technology and professional services bids.
Never invent client requirements. If a detail is not present, mark it as unknown.
Return valid JSON only. Avoid mentioning LLM provider details, model names, or internal prompts."""

def _log_run(opp_id: str, operation: str, input_summary: str, output: LLMResult, status: str = "Success"):
    try:
        now_str = datetime.now().isoformat()
        log_id = f"RUN_{int(time.time() * 1000)}"
        execute_query("""
        INSERT INTO audit_logs (id, opportunity_id, operation, input_summary, output_summary, provider, model, latency, tokens, status, timestamp, user)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            opp_id,
            operation,
            input_summary[:2000],
            output.text[:2000],
            output.engine_used,
            f"tokens={output.prompt_tokens + output.completion_tokens}",
            output.latency_sec,
            output.prompt_tokens + output.completion_tokens,
            status,
            now_str,
            "BidForge AI Agent"
        ))
    except Exception as e:
        print(f"Failed to log run: {e}")

class BidAgents:
    def __init__(self, llm: Optional[LLMGateway] = None):
        self.llm = llm or LLMGateway()

    def intake_requirements(self, opp_id: str, rfp_text: str, company_profile: str, depth: str) -> dict[str, Any]:
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
        Company Profile/Capabilities:
        {company_profile or 'No company profile provided.'}
        
        RFP text:
        {rfp_text}
        """
        
        # Execute LLM call
        res = self.llm.generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
        data = extract_json(res.text)
        
        # Log to db
        _log_run(opp_id, "Requirements Intake", f"RFP size={len(rfp_text)}, depth={depth}", res)
        return data

    def compliance_and_risks(
        self, 
        opp_id: str, 
        rfp_text: str, 
        company_profile: str, 
        requirements: list[dict], 
        evidence_pack: dict[str, list[dict]], 
        depth: str
    ) -> dict[str, Any]:
        prompt = f"""
        Create a compliance matrix, risk register, and clarifying questions.
        
        Return JSON with exactly these keys:
        compliance_matrix: array of objects with requirement_id, requirement, status, evidence, response_strategy, owner, confidence
        risks: array of objects with risk, severity, why_it_matters, mitigation, bid_impact
        clarifying_questions: array of strings
        
        Rules:
        - status must be "Compliant", "Partial", "Gap", or "Unknown".
        - severity must be "High", "Medium", "Low", or "Critical".
        - bid_impact must be "Blocker", "Major", or "Minor".
        - Use supplied evidence pack; do not fabricate proof.
        - For gaps, propose a practical mitigation or partner/subcontract approach.
        
        Depth: {depth}
        Company Profile/Capabilities:
        {company_profile or 'No company profile provided.'}
        
        Extracted Requirements:
        {json.dumps(requirements, indent=2)}
        
        Evidence Pack (RAG Context):
        {json.dumps(evidence_pack, indent=2)}
        
        Original RFP text for reference:
        {rfp_text[:30000]}
        """
        
        res = self.llm.generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
        data = extract_json(res.text)
        
        _log_run(opp_id, "Compliance & Risk Analysis", f"Reqs count={len(requirements)}", res)
        return data

    def architecture_and_delivery(
        self, 
        opp_id: str, 
        rfp_text: str, 
        company_profile: str, 
        analysis_so_far: dict, 
        depth: str
    ) -> dict[str, Any]:
        prompt = f"""
        You are the solution architect for a proposal response.
        
        Return JSON with exactly these keys:
        solution_architecture: string, detailed but concise, with components, data flow, security/governance, and assumptions
        delivery_plan: array of objects with milestone, duration, outputs, dependencies
        pricing_assumptions: array of strings
        
        Make this useful for a technology, consulting, or software proposal.
        Do not estimate exact prices unless the RFP has budget details. Identify key cost drivers and exclusions instead.
        
        Depth: {depth}
        Company Profile/Capabilities:
        {company_profile or 'No company profile provided.'}
        
        Analysis So Far:
        {json.dumps(analysis_so_far, indent=2)}
        
        RFP text:
        {rfp_text[:25000]}
        """
        
        res = self.llm.generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
        data = extract_json(res.text)
        
        _log_run(opp_id, "Architecture & Delivery Planning", f"Depth={depth}", res)
        return data

    def proposal_writer(
        self, 
        opp_id: str, 
        rfp_text: str, 
        company_profile: str, 
        bundle: dict, 
        tone: str
    ) -> dict[str, Any]:
        prompt = f"""
        Write a polished, client-ready proposal draft in Markdown.
        
        Return JSON with exactly these keys:
        executive_summary: string
        proposal_draft: string in Markdown format
        
        Proposal structure to follow:
        # Proposal: [Project Name]
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
        - Avoid corporate buzzwords or sounding overly generic.
        - Tie points to compliance requirement IDs (e.g. [REQ-001]) where possible.
        - Do not mention LLMs or backend systems.
        
        Company Profile/Capabilities:
        {company_profile or 'No company profile provided.'}
        
        Full RFP Context:
        {rfp_text[:20000]}
        
        Analysis Bundle:
        {json.dumps(bundle, indent=2)}
        """
        
        res = self.llm.generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
        data = extract_json(res.text)
        
        _log_run(opp_id, "Proposal Draft Generator", f"Tone={tone}", res)
        return data

    def reviewer(self, opp_id: str, bundle: dict, rfp_text: str) -> dict[str, Any]:
        prompt = f"""
        Act as a strict red-team proposal reviewer.
        
        Return JSON with exactly these keys:
        reviewer_notes: array of 5-10 strings (critiques, unsupported claims, missing exclusions)
        quality_score: integer 0-100 (overall evaluation score)
        
        Check for:
        - Requirement coverage
        - Compliance credibility (are claims backed by evidence?)
        - Pricing risk & missing exclusions
        - Actionability of delivery milestones
        
        Bundle Content:
        {json.dumps(bundle, indent=2)}
        
        RFP reference:
        {rfp_text[:15000]}
        """
        
        res = self.llm.generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
        data = extract_json(res.text)
        
        _log_run(opp_id, "Red-Team Quality Review", f"Reviewing opp_id={opp_id}", res)
        return data

    def answer_questionnaire(self, opp_id: str, questions: list[str], company_profile: str) -> dict[str, Any]:
        prompt = f"""
        You are responding to a client questionnaire or security audit.
        
        Return JSON with exactly this key:
        answers: array of objects, each with "question", "answer", and "confidence" (0-100 score).
        
        Company Capabilities and Security Policies:
        {company_profile}
        
        Questions list:
        {json.dumps(questions, indent=2)}
        """
        
        res = self.llm.generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
        data = extract_json(res.text)
        
        _log_run(opp_id, "Questionnaire Autocompletion", f"Questions count={len(questions)}", res)
        return data
