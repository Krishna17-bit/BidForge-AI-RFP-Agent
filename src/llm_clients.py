from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Optional, Any
import requests

from .config import settings
from .utils import truncate, extract_json

class LLMError(RuntimeError):
    pass

@dataclass
class LLMResult:
    text: str
    engine_used: str
    latency_sec: float
    prompt_tokens: int
    completion_tokens: int

class LLMGateway:
    """Unified multi-provider LLM gateway with mock fallback."""

    def __init__(self):
        self.temperature = settings.temperature
        self.provider = settings.llm_provider.lower()
        self.mock_mode = settings.mock_mode

    def generate(self, prompt: str, *, system: Optional[str] = None, json_mode: bool = False) -> LLMResult:
        t0 = time.time()
        prompt = truncate(prompt, settings.max_chars_per_prompt)
        
        if self.mock_mode or self.provider == "mock":
            res = self._mock(prompt, json_mode)
            latency = time.time() - t0
            return LLMResult(res, "mock", latency, len(prompt) // 4, len(res) // 4)

        errors: list[str] = []

        # Try designated provider
        try:
            if self.provider == "gemini":
                text = self._gemini(prompt, system, json_mode)
            elif self.provider == "openai":
                text = self._openai(prompt, system, json_mode)
            elif self.provider == "anthropic":
                text = self._anthropic(prompt, system, json_mode)
            elif self.provider == "groq":
                text = self._groq(prompt, system, json_mode)
            elif self.provider == "mistral":
                text = self._mistral(prompt, system, json_mode)
            elif self.provider == "ollama":
                text = self._ollama(prompt, system, json_mode)
            elif self.provider == "custom_openai":
                text = self._custom_openai(prompt, system, json_mode)
            else:
                raise LLMError(f"Unsupported provider: {self.provider}")
            
            latency = time.time() - t0
            return LLMResult(text, self.provider, latency, len(prompt) // 4, len(text) // 4)
        except Exception as exc:
            errors.append(f"Primary provider '{self.provider}' failed: {exc}")

        # Fallback to secondary if configured
        if settings.gemini_api_key and self.provider != "gemini":
            try:
                text = self._gemini(prompt, system, json_mode)
                latency = time.time() - t0
                return LLMResult(text, "gemini_fallback", latency, len(prompt) // 4, len(text) // 4)
            except Exception as exc:
                errors.append(f"Gemini fallback failed: {exc}")

        if settings.groq_api_key and self.provider != "groq":
            try:
                text = self._groq(prompt, system, json_mode)
                latency = time.time() - t0
                return LLMResult(text, "groq_fallback", latency, len(prompt) // 4, len(text) // 4)
            except Exception as exc:
                errors.append(f"Groq fallback failed: {exc}")

        # If everything fails, run mock mode so the pipeline doesn't break
        res = self._mock(prompt, json_mode)
        latency = time.time() - t0
        return LLMResult(res, "mock_fallback", latency, len(prompt) // 4, len(res) // 4)

    def _gemini(self, prompt: str, system: Optional[str], json_mode: bool) -> str:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        config_kwargs: dict[str, Any] = {"temperature": self.temperature}
        if system:
            config_kwargs["system_instruction"] = system
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        return getattr(response, "text", "") or ""

    def _openai(self, prompt: str, system: Optional[str], json_mode: bool) -> str:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": settings.openai_model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def _anthropic(self, prompt: str, system: Optional[str], json_mode: bool) -> str:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        messages = [{"role": "user", "content": prompt}]
        
        kwargs: dict[str, Any] = {
            "model": settings.anthropic_model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 4000,
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text or ""

    def _groq(self, prompt: str, system: Optional[str], json_mode: bool) -> str:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        kwargs: dict[str, Any] = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        try:
            completion = client.chat.completions.create(**kwargs)
        except Exception:
            # Fall back if json mode is not supported by groq model
            kwargs.pop("response_format", None)
            completion = client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content or ""

    def _mistral(self, prompt: str, system: Optional[str], json_mode: bool) -> str:
        if not settings.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY is not set.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.mistral_api_key}"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": settings.mistral_model,
            "messages": messages,
            "temperature": self.temperature
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        res = requests.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

    def _ollama(self, prompt: str, system: Optional[str], json_mode: bool) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": False
        }
        if json_mode:
            payload["format"] = "json"
            
        res = requests.post(f"{settings.ollama_base_url}/api/chat", json=payload)
        res.raise_for_status()
        return res.json()["message"]["content"]

    def _custom_openai(self, prompt: str, system: Optional[str], json_mode: bool) -> str:
        if not settings.custom_openai_base_url or not settings.custom_openai_api_key:
            raise ValueError("CUSTOM_OPENAI_BASE_URL and CUSTOM_OPENAI_API_KEY must be set.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.custom_openai_api_key}"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": settings.custom_openai_model or "custom-model",
            "messages": messages,
            "temperature": self.temperature
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        res = requests.post(f"{settings.custom_openai_base_url}/chat/completions", json=payload, headers=headers)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

    def _mock(self, prompt: str, json_mode: bool) -> str:
        """Smart context-aware mock generator."""
        # Detect what type of task we are answering based on keywords in prompt
        # We look for requested keys in JSON
        if "project_title" in prompt and "requirements" in prompt:
            # Opportunity Intake / Requirement Extraction
            # Extract possible keywords from the prompt to customize the mock response
            topic = "General Project Services"
            if "RAG" in prompt or "rag" in prompt or "AI" in prompt or "ai" in prompt:
                topic = "AI/RAG Document Search Engine"
            elif "security" in prompt or "compliance" in prompt:
                topic = "Enterprise Compliance Infrastructure"
            elif "website" in prompt or "portal" in prompt:
                topic = "State Portal Development Project"
                
            return json.dumps({
                "project_title": f"Mock: {topic}",
                "opportunity_summary": f"This is an automated analysis of the uploaded brief for the {topic}. The document outlines requirements for technical implementation, security audits, and delivery timelines.",
                "bid_recommendation": "Bid With Caution",
                "bid_score": 75,
                "win_themes": [
                    "Direct alignment with target solution requirements",
                    "Security compliance via local database design",
                    "Fast MVP turnaround within 3 weeks",
                    "Proven case studies in similar tech stacks"
                ],
                "requirements": [
                    {
                        "id": "REQ-001",
                        "text": "The solution must support parsing of PDF, DOCX, and CSV formats.",
                        "category": "Technical",
                        "priority": "Must",
                        "deliverable": "Document Loader Service",
                        "evidence_needed": "Case study demonstrating PDF layout extraction"
                    },
                    {
                        "id": "REQ-002",
                        "text": "All data must remain secure and local, with masked API logs.",
                        "category": "Security/Compliance",
                        "priority": "Must",
                        "deliverable": "Local SQLite caching database",
                        "evidence_needed": "Security policy documentation"
                    },
                    {
                        "id": "REQ-003",
                        "text": "The platform must export reports in Word (DOCX) and CSV formats.",
                        "category": "Delivery",
                        "priority": "Should",
                        "deliverable": "Export Center module",
                        "evidence_needed": "Sample generated reports"
                    },
                    {
                        "id": "REQ-004",
                        "text": "A human reviewer dashboard must approve sections before final submission.",
                        "category": "Delivery",
                        "priority": "Must",
                        "deliverable": "Streamlit workflow approval queue",
                        "evidence_needed": "Review log trail"
                    },
                    {
                        "id": "REQ-005",
                        "text": "Must complete first delivery phase in 15 days.",
                        "category": "General",
                        "priority": "Should",
                        "deliverable": "Project delivery plan and milestones",
                        "evidence_needed": "Agile sprint schedules"
                    }
                ]
            }, indent=2)

        elif "compliance_matrix" in prompt and "risks" in prompt:
            # Compliance and Risks
            return json.dumps({
                "compliance_matrix": [
                    {
                        "requirement_id": "REQ-001",
                        "requirement": "The solution must support parsing of PDF, DOCX, and CSV formats.",
                        "status": "Compliant",
                        "evidence": "Mapped to Document Ingestion Engine in core codebase using pypdf and python-docx.",
                        "response_strategy": "Highlight core ingestion components and file format limits.",
                        "owner": "Sarah Connor",
                        "confidence": 98
                    },
                    {
                        "requirement_id": "REQ-002",
                        "requirement": "All data must remain secure and local, with masked API logs.",
                        "status": "Compliant",
                        "evidence": "Uses local sqlite3 file database. Environment secrets are masked in configuration files.",
                        "response_strategy": "Detail encryption at rest and environment scrubbing.",
                        "owner": "Alex Mercer",
                        "confidence": 95
                    },
                    {
                        "requirement_id": "REQ-003",
                        "requirement": "The platform must export reports in Word (DOCX) and CSV formats.",
                        "status": "Compliant",
                        "evidence": "Implemented exporter using docx styling tables and pandas dataframes.",
                        "response_strategy": "Provide samples of generated docx file headers.",
                        "owner": "Sarah Connor",
                        "confidence": 100
                    },
                    {
                        "requirement_id": "REQ-004",
                        "requirement": "A human reviewer dashboard must allow approval before final submission.",
                        "status": "Compliant",
                        "evidence": "Interactive Streamlit pages track approved/rejected review queues in the db.",
                        "response_strategy": "Show mockup of approval checklist items.",
                        "owner": "Sarah Connor",
                        "confidence": 90
                    },
                    {
                        "requirement_id": "REQ-005",
                        "requirement": "Must complete first delivery phase in 15 days.",
                        "status": "Partial",
                        "evidence": "Our standard Phase 1 discovery takes 3-5 days; code baseline takes 10 days. Total fits 15 days, but schedule is tight.",
                        "response_strategy": "Propose early draft freeze on Day 4 to avoid code delays.",
                        "owner": "John Doe",
                        "confidence": 75
                    }
                ],
                "risks": [
                    {
                        "risk": "Tight 15-day delivery timeline.",
                        "severity": "Medium",
                        "why_it_matters": "Increases chance of QA bugs during compliance reports.",
                        "mitigation": "Establish daily syncs and immediate access to client documents on Day 1.",
                        "bid_impact": "Minor"
                    },
                    {
                        "risk": "Ambiguous scope of custom formats.",
                        "severity": "High",
                        "why_it_matters": "Client might introduce legacy scanned PDFs which need OCR.",
                        "mitigation": "Clarify that scanned documents are out of scope unless explicitly quoted.",
                        "bid_impact": "Major"
                    }
                ],
                "clarifying_questions": [
                    "Will there be scanned PDFs requiring OCR processing?",
                    "Are there custom schemas or templates required for the DOCX export?",
                    "Who is the technical contact for database security review?"
                ]
            }, indent=2)

        elif "solution_architecture" in prompt and "delivery_plan" in prompt:
            # Architecture and Delivery Plan
            return json.dumps({
                "solution_architecture": "The proposed architecture is built on a clean three-tier system: \n- **Ingestion Tier**: Multi-format loader parsing PDF and DOCX, caching raw texts locally.\n- **Storage Tier**: SQLite local filesystem database for configuration, compliance matrices, audit trails, and run logs.\n- **Agentic Orchestration Tier**: A multi-agent framework utilizing prompt abstraction layers for Gemini/Groq alongside TF-IDF retrieval for capability evidence lookup.",
                "delivery_plan": [
                    {
                        "milestone": "Phase 1: Discovery & Scope Freeze",
                        "duration": "3 days",
                        "outputs": "Final requirements mapping, clarifying questions, and seeded test data",
                        "dependencies": "Client SME availability"
                    },
                    {
                        "milestone": "Phase 2: Core MVP Integration",
                        "duration": "7 days",
                        "outputs": "Working local parser, db tracking, and Streamlit review page",
                        "dependencies": "API key inputs and sample documents"
                    },
                    {
                        "milestone": "Phase 3: Hardening & Export Testing",
                        "duration": "5 days",
                        "outputs": "QA audits, exported packages, and final handoff",
                        "dependencies": "Reviewer approval of MVP"
                    }
                ],
                "pricing_assumptions": [
                    "API key usage fees are billed directly to client accounts.",
                    "Excludes hosting infrastructure costs for post-handover environments.",
                    "Prices assume a standard agile milestone delivery model."
                ]
            }, indent=2)

        elif "proposal_draft" in prompt:
            # Proposal Writer
            return json.dumps({
                "executive_summary": "This proposal outlines our approach to building a secure, automated document decision and compliance workspace. We leverage a multi-agent framework to turn requirements into evidence-backed bid reports.",
                "proposal_draft": """# Proposal: Enterprise RAG and Bid Decision Platform

## Understanding of Requirements
The client requires a secure system to ingest RFPs, automatically extract deliverables, compile evidence-linked compliance reports, manage SME approvals, and export formatted Microsoft Word and CSV files.

## Proposed Solution
We propose BidForge AI, a local-first desktop and server workspace. It parses text using structured Python libraries, queries local database repositories, and interfaces with LLM gateways under strict privacy controls.

## Delivery Plan
- **Milestone 1: Discovery & Setup (Days 1-3)**: Initial setup, database schema activation, and brief parsing validation.
- **Milestone 2: Dashboard & Mapping (Days 4-10)**: Building requirements matrix, matching capabilities, and configuring LLM adapters.
- **Milestone 3: Review & Delivery (Days 11-15)**: Workflow approvals testing, DOCX exporter validation, and final handover.

## Compliance and Assumptions
Our response strategy maps directly to each requirement:
- *REQ-001 (Document parsing)*: 100% compliant.
- *REQ-002 (Local security)*: 100% compliant via sqlite3 file encryption.
- *REQ-003 (Word export)*: 100% compliant.
- *REQ-004 (Human reviews)*: 100% compliant.

## Key Risks and Mitigations
- **Schedule Risk (Medium)**: Mitigation is daily standups and scoping validation.
- **OCR Requirement (High)**: Mitigation is early confirmation of document quality.

## Questions Before Final Scope
1. Will there be legacy files that require OCR capabilities?
2. Are there specific docx style guides or logos to brand the exports?

## Why This Team
Our team possesses deep expertise in agentic workflows, compliance automation, and Streamlit UI design. We have successfully delivered similar systems for APEX FinTech and State Health departments.

## Next Steps
Upon approval of this proposal, we will proceed with the Discovery kickoff call and environment seeding.
"""
            }, indent=2)

        elif "reviewer_notes" in prompt:
            # Reviewer Notes
            return json.dumps({
                "reviewer_notes": [
                    "Requirements coverage is solid: all 5 extracted requirements are addressed in the proposed sections.",
                    "The Technical Approach matches our existing case studies (Apex FinTech).",
                    "A potential gap exists regarding OCR: proposal doesn't mention how it handles scanned images.",
                    "Recommend adding pricing exclusions explicitly to the appendix page.",
                    "Compliance matrix statuses are correctly linked to evidence citations."
                ],
                "quality_score": 85
            }, indent=2)

        else:
            return json.dumps({
                "status": "success",
                "message": "Mock operation completed. Add API keys in settings to trigger live models."
            }, indent=2)
