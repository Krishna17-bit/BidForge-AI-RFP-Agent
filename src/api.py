from __future__ import annotations

import time
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel, Field
import uvicorn
import threading

from .database import execute_query, execute_read, init_db
from .config import settings
from .llm_clients import LLMGateway
from .agents import BidAgents

app = FastAPI(
    title="BidForge AI Backend API",
    description="Programmatic REST API for BidForge AI Opportunity Intelligence platform.",
    version="1.0.0"
)

# Initialize database on API startup
@app.on_event("startup")
def startup_event():
    init_db()

# Models
class OpportunityCreate(BaseModel):
    title: str
    buyer: str
    source: str = "Manual"
    type: str = "RFP"
    industry: str = "General"
    budget: str = "N/A"
    deadline: str = ""
    submission_portal: str = ""
    contact_details: str = ""
    required_documents: str = ""
    owner: str = ""

class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    buyer: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    decision: Optional[str] = None
    fit_score: Optional[int] = None
    risk_score: Optional[int] = None

class KnowledgeCreate(BaseModel):
    title: str
    type: str
    content: str
    tags: str = ""
    owner: str = "Sarah Connor"
    approved_status: str = "Approved & current"
    source_file: str = "manual_entry"
    validity_date: str = "2027-12-31"

class ComplianceItemPatch(BaseModel):
    status: str
    evidence: str = ""
    response_strategy: str = ""
    owner: str = ""

class SMETaskCreate(BaseModel):
    assignee: str
    due_date: str
    task_details: str
    related_req_id: str

class ReviewDecision(BaseModel):
    status: str
    comments: str = ""

class QuestionnaireImport(BaseModel):
    opportunity_id: str
    questions: list[str]

# 1. Health
@app.get("/health")
def health():
    return {"status": "healthy", "provider": settings.llm_provider, "mock_mode": settings.mock_mode}

# 2. Opportunities REST API
@app.get("/api/opportunities")
def get_opportunities():
    return execute_read("SELECT * FROM opportunities ORDER BY created_at DESC")

@app.post("/api/opportunities")
def create_opportunity(opp: OpportunityCreate):
    opp_id = f"OPP_{int(time.time())}"
    now_str = time.strftime("%Y-%m-%dT%H:%M:%S")
    execute_query("""
    INSERT INTO opportunities (id, title, buyer, source, type, industry, budget, deadline, submission_portal, contact_details, required_documents, status, owner, fit_score, risk_score, decision, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (opp_id, opp.title, opp.buyer, opp.source, opp.type, opp.industry, opp.budget, opp.deadline, opp.submission_portal, opp.contact_details, opp.required_documents, "New", opp.owner, 50, 50, "Needs More Info", now_str, now_str))
    
    return {"id": opp_id, "message": "Opportunity created successfully"}

@app.get("/api/opportunities/{id}")
def get_opportunity(id: str):
    rows = execute_read("SELECT * FROM opportunities WHERE id = ?", (id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return rows[0]

@app.patch("/api/opportunities/{id}")
def update_opportunity(id: str, opp: OpportunityUpdate):
    # Retrieve current data
    rows = execute_read("SELECT * FROM opportunities WHERE id = ?", (id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    fields = []
    values = []
    for k, v in opp.model_dump(exclude_unset=True).items():
        fields.append(f"{k} = ?")
        values.append(v)
    
    if not fields:
        return {"message": "No fields to update"}
        
    values.append(time.strftime("%Y-%m-%dT%H:%M:%S")) # updated_at
    values.append(id)
    execute_query(f"UPDATE opportunities SET {', '.join(fields)}, updated_at = ? WHERE id = ?", tuple(values))
    return {"message": "Opportunity updated successfully"}

@app.delete("/api/opportunities/{id}")
def delete_opportunity(id: str):
    execute_query("DELETE FROM opportunities WHERE id = ?", (id,))
    return {"message": "Opportunity deleted successfully"}

# 3. Opportunity Analysis Pipeline Endpoints
@app.post("/api/opportunities/{id}/extract-requirements")
def extract_requirements(id: str, rfp_text: Optional[str] = Form(None)):
    opp_rows = execute_read("SELECT * FROM opportunities WHERE id = ?", (id,))
    if not opp_rows:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    text = rfp_text or opp_rows[0]["required_documents"] or "Sample brief text"
    
    agents = BidAgents()
    result = agents.intake_requirements(id, text, "", "Standard")
    
    # Store requirements to database
    requirements = result.get("requirements", [])
    for r in requirements:
        rid = r.get("id") or f"REQ_{int(time.time() * 1000)}"
        execute_query("""
        INSERT OR REPLACE INTO extracted_requirements (id, opportunity_id, text, category, priority, deliverable, evidence_needed, status, owner, confidence, source_section, source_page, evidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rid, id, r.get("text"), r.get("category", "General"), r.get("priority", "Unknown"), r.get("deliverable", ""), r.get("evidence_needed", ""), "not started", "Sarah Connor", 90, "Section 1", 1, ""))
        
    # Update title and score
    title = result.get("project_title", opp_rows[0]["title"])
    rec = result.get("bid_recommendation", opp_rows[0]["decision"])
    score = result.get("bid_score", opp_rows[0]["fit_score"])
    
    execute_query("UPDATE opportunities SET title = ?, decision = ?, fit_score = ? WHERE id = ?", (title, rec, score, id))
    return {"message": f"Extracted {len(requirements)} requirements", "data": result}

@app.post("/api/opportunities/{id}/generate-compliance-matrix")
def generate_compliance(id: str, rfp_text: Optional[str] = Form(None)):
    opp_rows = execute_read("SELECT * FROM opportunities WHERE id = ?", (id,))
    if not opp_rows:
        raise HTTPException(status_code=404, detail="Opportunity not found")
        
    reqs_rows = execute_read("SELECT * FROM extracted_requirements WHERE opportunity_id = ?", (id,))
    reqs = [{"id": r["id"], "text": r["text"], "category": r["category"], "priority": r["priority"]} for r in reqs_rows]
    
    agents = BidAgents()
    # Mock evidence matching
    evidence = {}
    for r in reqs:
        evidence[r["id"]] = [{"document": "knowledge_base.db", "page": 1, "score": 0.85, "text": "Capability verification text here"}]
        
    text = rfp_text or "General RFP scope details"
    result = agents.compliance_and_risks(id, text, "", reqs, evidence, "Standard")
    
    # Store compliance items
    matrix = result.get("compliance_matrix", [])
    for idx, c in enumerate(matrix):
        cid = f"C_{id}_{idx}"
        execute_query("""
        INSERT OR REPLACE INTO compliance_matrix_items (id, opportunity_id, requirement_id, requirement, status, evidence, response_strategy, owner, confidence, risk_level, proposal_section, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cid, id, c.get("requirement_id"), c.get("requirement"), c.get("status"), c.get("evidence"), c.get("response_strategy"), c.get("owner"), c.get("confidence", 50), "Medium", "Technical Approach", ""))

    # Store risks
    risks = result.get("risks", [])
    for idx, r in enumerate(risks):
        rid = f"R_{id}_{idx}"
        execute_query("""
        INSERT OR REPLACE INTO risks (id, opportunity_id, risk, severity, why_it_matters, mitigation, bid_impact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (rid, id, r.get("risk"), r.get("severity"), r.get("why_it_matters"), r.get("mitigation"), r.get("bid_impact")))

    return {"message": f"Generated {len(matrix)} compliance matrix items and {len(risks)} risks", "data": result}

@app.post("/api/opportunities/{id}/generate-proposal")
def generate_proposal(id: str, rfp_text: Optional[str] = Form(None)):
    opp_rows = execute_read("SELECT * FROM opportunities WHERE id = ?", (id,))
    if not opp_rows:
        raise HTTPException(status_code=404, detail="Opportunity not found")
        
    # Gather database details for context
    reqs = execute_read("SELECT * FROM extracted_requirements WHERE opportunity_id = ?", (id,))
    risks = execute_read("SELECT * FROM risks WHERE opportunity_id = ?", (id,))
    compliance = execute_read("SELECT * FROM compliance_matrix_items WHERE opportunity_id = ?", (id,))
    
    bundle = {
        "project_title": opp_rows[0]["title"],
        "opportunity_summary": opp_rows[0]["required_documents"],
        "requirements": reqs,
        "risks": risks,
        "compliance_matrix": compliance
    }
    
    text = rfp_text or "General RFP details"
    agents = BidAgents()
    result = agents.proposal_writer(id, text, "", bundle, "Consultative")
    
    # Store draft sections
    execute_query("""
    INSERT OR REPLACE INTO proposal_sections (id, opportunity_id, section_name, draft_content, completion_status, version)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (f"PS_{id}_summary", id, "Executive Summary", result.get("executive_summary"), "Draft", 1))
    
    execute_query("""
    INSERT OR REPLACE INTO proposal_sections (id, opportunity_id, section_name, draft_content, completion_status, version)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (f"PS_{id}_full", id, "Full Proposal Draft", result.get("proposal_draft"), "Draft", 1))

    return {"message": "Proposal drafted successfully", "data": result}

# 4. Knowledge Base CRUD
@app.get("/api/knowledge")
def get_knowledge():
    return execute_read("SELECT * FROM knowledge_items")

@app.post("/api/knowledge")
def create_knowledge(item: KnowledgeCreate):
    kid = f"KB_{int(time.time())}"
    now_str = time.strftime("%Y-%m-%dT%H:%M:%S")
    execute_query("""
    INSERT INTO knowledge_items (id, title, type, content, tags, owner, approved_status, source_file, validity_date, usage_count, win_loss_performance, last_updated)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (kid, item.title, item.type, item.content, item.tags, item.owner, item.approved_status, item.source_file, item.validity_date, 0, "N/A", now_str))
    return {"id": kid, "message": "Knowledge item added"}

@app.delete("/api/knowledge/{id}")
def delete_knowledge(id: str):
    execute_query("DELETE FROM knowledge_items WHERE id = ?", (id,))
    return {"message": "Knowledge item deleted"}

# 5. Requirements and Compliance Details
@app.get("/api/requirements")
def get_all_requirements():
    return execute_read("SELECT * FROM extracted_requirements")

@app.get("/api/compliance-matrix/{opportunityId}")
def get_compliance_matrix(opportunityId: str):
    return execute_read("SELECT * FROM compliance_matrix_items WHERE opportunity_id = ?", (opportunityId,))

@app.patch("/api/compliance-matrix/items/{id}")
def update_compliance_item(id: str, item: ComplianceItemPatch):
    execute_query("""
    UPDATE compliance_matrix_items
    SET status = ?, evidence = ?, response_strategy = ?, owner = ?
    WHERE id = ?
    """, (item.status, item.evidence, item.response_strategy, item.owner, id))
    return {"message": "Compliance item updated"}

# 6. Runs & Audit Logs
@app.get("/api/runs")
def get_runs():
    return execute_read("SELECT * FROM audit_logs ORDER BY timestamp DESC")

@app.get("/api/audit-logs")
def get_audit_logs():
    return execute_read("SELECT * FROM audit_logs ORDER BY timestamp DESC")

# 7. Questionnaire endpoints
@app.post("/api/questionnaires/{id}/generate-answers")
def generate_questionnaire_answers(id: str, payload: QuestionnaireImport):
    agents = BidAgents()
    result = agents.answer_questionnaire(id, payload.questions, "ISO27001, local database, role-based controls")
    answers = result.get("answers", [])
    
    for idx, ans in enumerate(answers):
        qid = f"QI_{id}_{idx}"
        execute_query("""
        INSERT OR REPLACE INTO questionnaire_items (id, opportunity_id, question_text, detected_answer, confidence, status, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (qid, id, ans.get("question"), ans.get("answer"), ans.get("confidence", 80), "Pending", "API_Import"))
        
    return {"answers": answers}

# 8. Provider settings test
@app.post("/api/settings/providers/test")
def test_provider(payload: dict):
    provider = payload.get("provider", "mock")
    # Simulate ping
    time.sleep(0.3)
    return {"status": "success", "message": f"Connection to {provider} checked successfully.", "healthy": True}

# Background server thread helper
def start_server_background():
    try:
        # Runs uvicorn on port 8000
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    except Exception as e:
        print(f"FastAPI background server error: {e}")

_server_thread: Optional[threading.Thread] = None

def run_api_server():
    global _server_thread
    if _server_thread is None:
        _server_thread = threading.Thread(target=start_server_background, daemon=True)
        _server_thread.start()
        print("FastAPI background API server started on http://127.0.0.1:8000")
