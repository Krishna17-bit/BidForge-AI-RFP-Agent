from __future__ import annotations

from typing import Any

from .agents import BidAgents, heuristic_requirements
from .document_loader import LoadedDocument
from .llm_clients import LLMError
from .retrieval import EvidenceIndex
from .schemas import AnalysisBundle


def _merge_dicts(*parts: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for part in parts:
        if isinstance(part, dict):
            merged.update({k: v for k, v in part.items() if v is not None})
    return merged


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return []


class BidOrchestrator:
    def __init__(self):
        self.agents = BidAgents()

    def run(
        self,
        rfp_docs: list[LoadedDocument],
        knowledge_docs: list[LoadedDocument],
        company_profile: str,
        depth: str = "Deep",
        tone: str = "Consultative, confident, concise",
        progress_callback=None,
    ) -> dict[str, Any]:
        all_docs = rfp_docs + knowledge_docs
        rfp_text = "\n\n".join([f"# {d.name}\n{d.text}" for d in rfp_docs])
        knowledge_text = "\n\n".join([f"# {d.name}\n{d.text}" for d in knowledge_docs])
        profile = (company_profile or "").strip()
        if knowledge_text.strip():
            profile = f"{profile}\n\nUploaded company/capability knowledge:\n{knowledge_text[:30000]}".strip()

        # Keep requirement-source context separate from capability proof.
        # This makes the Evidence tab clearer: CV/profile/case-study matches
        # appear first, while RFP text is labeled only as source context.
        profile_doc = None
        if (company_profile or "").strip():
            profile_doc = LoadedDocument(
                name="typed_company_profile.txt",
                text=(company_profile or "").strip(),
                pages=[{"page": 1, "text": (company_profile or "").strip()}],
            )
        capability_docs = list(knowledge_docs)
        if profile_doc is not None:
            capability_docs.append(profile_doc)

        capability_index = EvidenceIndex(capability_docs) if capability_docs else None
        opportunity_index = EvidenceIndex(rfp_docs) if rfp_docs else None

        try:
            if progress_callback:
                progress_callback("Extracting requirements and bid fit...")
            intake = self.agents.intake_requirements(rfp_text, profile, depth)
        except LLMError:
            intake = heuristic_requirements(rfp_text, profile)
            intake["reviewer_notes"] = ["Running in offline heuristic mode because no valid API key was found."]
        except Exception as exc:
            intake = heuristic_requirements(rfp_text, profile)
            intake["reviewer_notes"] = [f"Primary analysis failed, so offline heuristic mode was used: {exc}"]

        requirements = _as_list(intake.get("requirements"))

        if progress_callback:
            progress_callback("Mapping evidence to every requirement...")
        evidence_pack: dict[str, list[dict]] = {}
        for req in requirements:
            rid = str(req.get("id", "REQ"))
            query = f"{req.get('text','')} {req.get('deliverable','')} {req.get('evidence_needed','')}"
            capability_hits = []
            if capability_index is not None:
                capability_hits = [
                    {**hit, "evidence_type": "Capability proof"}
                    for hit in capability_index.search(query, k=4)
                ]
            opportunity_hits = []
            if opportunity_index is not None:
                opportunity_hits = [
                    {**hit, "evidence_type": "RFP source context"}
                    for hit in opportunity_index.search(query, k=2)
                ]
            evidence_pack[rid] = capability_hits + opportunity_hits

        try:
            if progress_callback:
                progress_callback("Building compliance matrix, risk register, and clarification questions...")
            compliance = self.agents.compliance_and_risks(rfp_text, profile, requirements, evidence_pack, depth)
        except Exception as exc:
            compliance = self._fallback_compliance(requirements, evidence_pack, exc)

        analysis_so_far = _merge_dicts(intake, compliance, {"evidence_pack": evidence_pack})
        try:
            if progress_callback:
                progress_callback("Designing solution architecture and delivery plan...")
            architecture = self.agents.architecture_and_delivery(rfp_text, profile, analysis_so_far, depth)
        except Exception as exc:
            architecture = self._fallback_architecture(exc)

        draft_input = _merge_dicts(intake, compliance, architecture)
        try:
            if progress_callback:
                progress_callback("Writing proposal draft...")
            proposal = self.agents.proposal_writer(rfp_text, profile, draft_input, tone)
        except Exception as exc:
            proposal = self._fallback_proposal(draft_input, exc)

        bundle_dict = _merge_dicts(intake, compliance, architecture, proposal, {"evidence_pack": evidence_pack})
        try:
            if progress_callback:
                progress_callback("Running final proposal quality review...")
            review = self.agents.reviewer(bundle_dict, rfp_text)
        except Exception as exc:
            review = {"reviewer_notes": [f"Automated review unavailable: {exc}"], "quality_score": int(bundle_dict.get("bid_score", 50) or 50)}

        final = _merge_dicts(bundle_dict, review)
        try:
            validated = AnalysisBundle(**{k: v for k, v in final.items() if k in AnalysisBundle.model_fields})
            normalized = validated.model_dump()
        except Exception:
            normalized = final

        normalized["evidence_pack"] = evidence_pack
        normalized["source_documents"] = [d.name for d in all_docs]
        return normalized

    @staticmethod
    def _fallback_compliance(requirements: list[dict], evidence_pack: dict[str, list[dict]], exc: Exception) -> dict[str, Any]:
        matrix = []
        for r in requirements:
            rid = r.get("id", "REQ")
            ev = evidence_pack.get(str(rid), [])
            matrix.append({
                "requirement_id": rid,
                "requirement": r.get("text", ""),
                "status": "Unknown" if not ev else "Partial",
                "evidence": ev[0]["text"][:220] if ev else "No direct evidence found in uploaded documents.",
                "response_strategy": "Confirm scope, provide implementation approach, and attach relevant proof before submission.",
                "owner": "Proposal lead / technical lead",
                "confidence": 45 if ev else 25,
            })
        return {
            "compliance_matrix": matrix,
            "risks": [{
                "risk": "Some compliance statuses could not be verified automatically.",
                "severity": "Medium",
                "why_it_matters": "Unsupported claims weaken bid credibility.",
                "mitigation": "Add capability documents, case studies, or internal references before final submission.",
                "bid_impact": "Major",
            }],
            "clarifying_questions": [
                "What are the mandatory vs optional requirements?",
                "What is the expected budget range and decision timeline?",
                "What integrations, data access, and security constraints are non-negotiable?",
            ],
            "reviewer_notes": [f"Compliance agent fallback used: {exc}"],
        }

    @staticmethod
    def _fallback_architecture(exc: Exception) -> dict[str, Any]:
        return {
            "solution_architecture": "Proposed delivery should begin with discovery, requirement validation, architecture design, implementation, QA, deployment, documentation, and handover. Add a more specific architecture after connecting API keys.",
            "delivery_plan": [
                {"milestone": "Discovery and scope freeze", "duration": "3-5 days", "outputs": "Final requirements, assumptions, success criteria", "dependencies": "Client stakeholder access"},
                {"milestone": "Prototype / MVP", "duration": "1-2 weeks", "outputs": "Working prototype and review demo", "dependencies": "Access to data, APIs, sample documents"},
                {"milestone": "Production hardening", "duration": "1-2 weeks", "outputs": "QA, deployment, documentation, handover", "dependencies": "Client feedback and acceptance tests"},
            ],
            "pricing_assumptions": [
                "Pricing depends on number of workflows, integrations, document volume, compliance needs, and support period.",
                f"Architecture agent fallback used: {exc}",
            ],
        }

    @staticmethod
    def _fallback_proposal(bundle: dict[str, Any], exc: Exception) -> dict[str, Any]:
        title = bundle.get("project_title", "Client Project")
        summary = bundle.get("opportunity_summary", "The uploaded brief has been analyzed for requirements, risks, and delivery planning.")
        reqs = bundle.get("requirements", [])[:8]
        req_md = "\n".join([f"- **{r.get('id','REQ')}**: {r.get('text','')}" for r in reqs])
        draft = f"""# Proposal: {title}

## Understanding of Requirements
{summary}

Key requirements identified:
{req_md or '- Requirements need confirmation.'}

## Proposed Solution
{bundle.get('solution_architecture','A phased delivery approach is recommended.')}

## Delivery Plan
"""
        for m in bundle.get("delivery_plan", []):
            draft += f"\n- **{m.get('milestone','Milestone')}** ({m.get('duration','TBD')}): {m.get('outputs','')}"
        draft += "\n\n## Risks and Assumptions\n"
        for r in bundle.get("risks", []):
            draft += f"\n- **{r.get('severity','Medium')}**: {r.get('risk','')} — {r.get('mitigation','')}"
        draft += "\n\n## Questions Before Final Scope\n"
        for q in bundle.get("clarifying_questions", []):
            draft += f"\n- {q}"
        draft += f"\n\n> Draft fallback note: proposal writer unavailable: {exc}\n"
        return {"executive_summary": summary, "proposal_draft": draft}
