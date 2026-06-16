from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "bidforge.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Opportunities
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS opportunities (
        id TEXT PRIMARY KEY,
        title TEXT,
        buyer TEXT,
        source TEXT,
        type TEXT,
        industry TEXT,
        budget TEXT,
        deadline TEXT,
        submission_portal TEXT,
        contact_details TEXT,
        required_documents TEXT,
        status TEXT,
        owner TEXT,
        fit_score INTEGER,
        risk_score INTEGER,
        decision TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    
    # 2. Extracted Requirements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS extracted_requirements (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        text TEXT,
        category TEXT,
        priority TEXT,
        deliverable TEXT,
        evidence_needed TEXT,
        status TEXT,
        owner TEXT,
        confidence INTEGER,
        source_section TEXT,
        source_page INTEGER,
        evidence TEXT,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    )
    """)
    
    # 3. Compliance Matrix Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compliance_matrix_items (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        requirement_id TEXT,
        requirement TEXT,
        status TEXT,
        evidence TEXT,
        response_strategy TEXT,
        owner TEXT,
        confidence INTEGER,
        risk_level TEXT,
        proposal_section TEXT,
        notes TEXT,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    )
    """)
    
    # 4. Risks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS risks (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        risk TEXT,
        severity TEXT,
        why_it_matters TEXT,
        mitigation TEXT,
        bid_impact TEXT,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    )
    """)
    
    # 5. Knowledge Items (Evidence Library)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_items (
        id TEXT PRIMARY KEY,
        title TEXT,
        type TEXT,
        content TEXT,
        tags TEXT,
        owner TEXT,
        approved_status TEXT,
        source_file TEXT,
        validity_date TEXT,
        usage_count INTEGER,
        win_loss_performance TEXT,
        last_updated TEXT
    )
    """)
    
    # 6. Proposal Sections
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proposal_sections (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        section_name TEXT,
        draft_content TEXT,
        completion_status TEXT,
        version INTEGER,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    )
    """)
    
    # 7. SME Tasks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sme_tasks (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        assignee TEXT,
        due_date TEXT,
        task_details TEXT,
        related_req_id TEXT,
        status TEXT,
        comments TEXT,
        attachments TEXT,
        decision TEXT,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    )
    """)
    
    # 8. Questionnaire Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questionnaire_items (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        question_text TEXT,
        detected_answer TEXT,
        confidence INTEGER,
        status TEXT,
        source_file TEXT,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    )
    """)
    
    # 9. Win/Loss Records
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS win_loss_records (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        outcome TEXT,
        reason TEXT,
        competitor TEXT,
        buyer_feedback TEXT,
        price_feedback TEXT,
        strengths TEXT,
        weaknesses TEXT,
        lessons_learned TEXT,
        reusable_content TEXT,
        kb_updates TEXT,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
    )
    """)
    
    # 10. Audit Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        opportunity_id TEXT,
        operation TEXT,
        input_summary TEXT,
        output_summary TEXT,
        provider TEXT,
        model TEXT,
        latency REAL,
        tokens INTEGER,
        status TEXT,
        timestamp TEXT,
        user TEXT
    )
    """)
    
    # 11. Eval Runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eval_runs (
        id TEXT PRIMARY KEY,
        timestamp TEXT,
        eval_type TEXT,
        accuracy_score REAL,
        comments TEXT
    )
    """)
    
    # 12. Provider Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS provider_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def execute_query(query: str, params: tuple = ()) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount

def execute_read(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

def seed_demo_data():
    # Only seed if no opportunities exist
    existing = execute_read("SELECT count(*) as count FROM opportunities")
    if existing and existing[0]["count"] > 0:
        return
        
    init_db()
    now_str = datetime.now().isoformat()
    
    # Define sample opportunities
    opps = [
        ("OPP-001", "Enterprise RAG Intelligence System", "Global Logistics Corp", "Upwork Job Post", "Freelance job", "Tech Services", "50,000 USD", "2026-07-20", "Upwork Portal", "hiring@globallogistics.com", "Proposal, Case Studies, Security Questionnaire", "Bid decision", "Sarah Connor", 88, 20, "Strong bid", now_str, now_str),
        ("OPP-002", "State Health Department Portal RFP", "Department of Health", "Tender Notice", "RFP", "GovCon", "350,000 USD", "2026-08-15", "GovTenders.gov", "rfp-contact@health.gov", "Technical Response, Compliance Matrix, Price Proposal, Past Performance", "Reviewing", "John Doe", 75, 45, "Bid with caution", now_str, now_str),
        ("OPP-003", "AI Customer Support Agent Integration", "Apex FinTech", "Client Brief", "Client brief", "Finance", "25,000 USD", "2026-06-30", "Email to BD", "contact@apexfintech.com", "Proposal, MSA, SLA draft", "Won", "Sarah Connor", 92, 10, "Strong bid", now_str, now_str),
        ("OPP-004", "Gov Cloud Security Questionnaire", "Federal Agency", "Security Questionnaire", "Security questionnaire", "GovCon", "N/A", "2026-07-10", "Secure Upload Link", "sec-audit@gov.mil", "Completed XLS spreadsheet, ISO Certs", "Proposal drafting", "Alex Mercer", 62, 50, "Bid with caution", now_str, now_str),
        ("OPP-005", "Distributed Blockchain Ledger Tender", "Metro Transit Authority", "Tender RFP", "Tender", "Transit", "180,000 USD", "2026-09-01", "Procurement Portal", "transit-bid@metro.org", "Technical approach, Financial offer, Security clearance", "No-bid", "John Doe", 35, 80, "No-bid", now_str, now_str),
    ]
    
    for o in opps:
        execute_query("""
        INSERT INTO opportunities (id, title, buyer, source, type, industry, budget, deadline, submission_portal, contact_details, required_documents, status, owner, fit_score, risk_score, decision, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, o)
        
    # Extracted Requirements for OPP-001
    reqs_opp1 = [
        ("REQ-101", "OPP-001", "System must extract requirements from PDFs and DOCX files automatically with high accuracy.", "Technical", "Must", "Automated document parser engine", "Case study on PDF/DOCX processing pipelines", "mapped", "Sarah Connor", 90, "Section 3.1", 2, "Yes, we have implemented this in Apex FinTech project."),
        ("REQ-102", "OPP-001", "RAG engine must enforce tenant-level role-based access control (RBAC).", "Security/Compliance", "Must", "RBAC Auth integration", "ISO 27001 policy on access controls", "gap", "Alex Mercer", 75, "Section 4.2", 5, "We do not have a pre-built multi-tenant RAG model, but we have Single-Tenant RBAC ready. Needs customization."),
        ("REQ-103", "OPP-001", "A human review dashboard must allow manual compliance edits and review decisions before export.", "Delivery", "Must", "Compliance editing interface", "Demo app showcasing UI edits", "mapped", "Sarah Connor", 95, "Section 3.4", 3, "Developed identical system for Client Apex."),
        ("REQ-104", "OPP-001", "Must export proposals in Microsoft Word (.docx) and CSV formats.", "Delivery", "Should", "Export center utility", "Code base export scripts", "mapped", "Sarah Connor", 99, "Section 5.1", 7, "Our standard template supports docx and csv."),
        ("REQ-105", "OPP-001", "Pricing must support both fixed-price milestones and retainer models.", "General", "Should", "Pricing model assumptions", "Previous billing structures", "mapped", "John Doe", 80, "Section 6", 8, "Yes, standard models support this."),
    ]
    
    for r in reqs_opp1:
        execute_query("""
        INSERT INTO extracted_requirements (id, opportunity_id, text, category, priority, deliverable, evidence_needed, status, owner, confidence, source_section, source_page, evidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, r)
        
    # Compliance items for OPP-001
    comp_opp1 = [
        ("C-101", "OPP-001", "REQ-101", "System must extract requirements from PDFs and DOCX files automatically with high accuracy.", "Compliant", "Mapped to File Extraction Engine from our Core Library", "Build clean parser wrapper", "Sarah Connor", 95, "Low", "Technical Approach", "Verified in pre-sales demo"),
        ("C-102", "OPP-001", "REQ-102", "RAG engine must enforce tenant-level role-based access control (RBAC).", "Partial", "Single-tenant Auth configuration exists; Multi-tenant requires 3-5 days custom development", "Develop tenant isolation mapping layer", "Alex Mercer", 70, "Medium", "Security & Governance", "Will outline in proposed architecture"),
        ("C-103", "OPP-001", "REQ-103", "A human review dashboard must allow manual compliance edits and review decisions before export.", "Compliant", "Streamlit UI features inline tables and stateful edits", "Use interactive pandas dataframes", "Sarah Connor", 95, "Low", "Understanding of Requirements", "Fully implemented in current build"),
        ("C-104", "OPP-001", "REQ-104", "Must export proposals in Microsoft Word (.docx) and CSV formats.", "Compliant", "We use python-docx and pandas to write files locally and bundle them in a ZIP archive", "Save output to outputs/ directory", "Sarah Connor", 100, "Low", "Delivery Plan", "Standard exporter module in use"),
        ("C-105", "OPP-001", "REQ-105", "Pricing must support both fixed-price milestones and retainer models.", "Compliant", "Standard fee structure includes Milestones 1-3 fixed and monthly operations retainer", "Provide pricing breakdown format", "John Doe", 90, "Low", "Pricing & Assumptions", "Reflected in pricing assumptions"),
    ]
    
    for c in comp_opp1:
        execute_query("""
        INSERT INTO compliance_matrix_items (id, opportunity_id, requirement_id, requirement, status, evidence, response_strategy, owner, confidence, risk_level, proposal_section, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, c)
        
    # Risks for OPP-001
    risks_opp1 = [
        ("R-001", "OPP-001", "Vague multi-tenant RBAC requirement", "High", "Multi-tenant logic is highly custom and can lead to scope creep.", "Propose a clear Single-Tenant architecture or cap the scope of tenant isolation to 3 logical groups.", "Major"),
        ("R-002", "OPP-001", "Tight deadline of 20 days", "Medium", "Rushing development could introduce vulnerabilities or compromise compliance reporting.", "Establish a phased rollout plan with basic search on Week 2 and advanced exports on Week 3.", "Minor"),
    ]
    for r in risks_opp1:
        execute_query("""
        INSERT INTO risks (id, opportunity_id, risk, severity, why_it_matters, mitigation, bid_impact)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, r)
        
    # Knowledge Items (Evidence Library)
    kb = [
        ("KB-001", "Document Extraction Engine Details", "Technical approach", "Our proprietary document loader parses text from PDFs (using pypdf), DOCX (using python-docx), and raw TXT/CSV. It splits pages using page dividers and extracts text tables dynamically to preserve grid compliance formatting. We support file uploads up to 50MB and handle complex table structures by merging row cells with pipe dividers.", "pdf, docx, loader, parser, tables", "Sarah Connor", "Approved & current", "tech_stack_docs.docx", "2027-12-31", 12, "Won APEX-2025, Won HEALTH-2024", now_str),
        ("KB-002", "Standard Security and ISO Policy", "Security policy", "We follow SOC2 and ISO 27001 principles. All local databases are encrypted, and API keys are stored in a masked environment file (.env). We do not send raw documents to public LLMs without tenant-isolation tags and explicit user confirmation. All outbound prompt text is truncated at 70,000 characters to prevent overflow and enforce data safety limits.", "security, policy, ISO27001, SOC2, local", "Alex Mercer", "Approved & current", "security_charter.txt", "2028-01-01", 8, "Passed 3 audits", now_str),
        ("KB-003", "Apex FinTech Success Case Study", "Case Study", "We designed and implemented a local RAG pipeline for Apex FinTech. The solution processed over 4,000 loan documents daily, extracted compliance clauses with 96.4% recall, and mapped them to their corporate evidence rules. Built using Streamlit and a local SQLite caching db. The project was delivered in 4 weeks and resulted in a 40% reduction in manual audit times.", "case study, fintech, RAG, SQLite, success", "Sarah Connor", "Approved & current", "case_apex_fintech.md", "2027-06-30", 15, "Apex project won 2025", now_str),
        ("KB-004", "Milestone Delivery Methodology", "Technical approach", "We follow an agile three-phase delivery model: Phase 1 (Discovery & Scope Freeze) - 3-5 days; Phase 2 (Core MVP & Review Demo) - 1-2 weeks; Phase 3 (Hardening, QA, & Handover) - 1-2 weeks. Every milestone requires a formal User Acceptance Test (UAT) sign-off before subsequent phases commence.", "agile, methodology, timeline, delivery", "John Doe", "Approved & current", "delivery_guidelines.txt", "2027-12-31", 5, "Used on all contracts", now_str),
        ("KB-005", "Standard Pricing Exclusions", "Exclusions", "Our cost estimates exclude third-party API licensing fees (e.g. paid OpenAI/Anthropic keys), cloud hosting infrastructure costs, customized multi-tenant domain integrations (unless explicitly costed), and ongoing post-launch maintenance beyond the 30-day warranty window.", "pricing, exclusions, terms", "John Doe", "Approved & current", "billing_policy.txt", "2026-12-31", 9, "N/A", now_str),
    ]
    for k in kb:
        execute_query("""
        INSERT INTO knowledge_items (id, title, type, content, tags, owner, approved_status, source_file, validity_date, usage_count, win_loss_performance, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, k)

    # Proposal Sections for OPP-001
    sections_opp1 = [
        ("PS-001", "OPP-001", "Executive Summary", "This proposal details our solution for the Enterprise RAG Intelligence System requested by Global Logistics Corp. Our platform, BidForge AI, provides a local-first, multi-agent workspace specifically customized for logistics data compliance.", "Approved", 1),
        ("PS-002", "OPP-001", "Understanding of Requirements", "Global Logistics Corp requires an automated system to parse PDF/DOCX files, extract requirements with high confidence, establish compliance matrices, and manage reviewer workflows, all while adhering to tight data isolation policies.", "Review", 1),
        ("PS-003", "OPP-001", "Technical Approach", "We propose a localized pipeline consisting of: 1) A document ingestion layer using python-docx and pypdf; 2) A TF-IDF local vector retrieval index for zero-cost semantic search over company capability profiles; 3) A multi-provider LLM gateway supporting secure cloud APIs (Gemini, OpenAI) or offline mock models.", "Draft", 1),
    ]
    for s in sections_opp1:
        execute_query("""
        INSERT INTO proposal_sections (id, opportunity_id, section_name, draft_content, completion_status, version)
        VALUES (?, ?, ?, ?, ?, ?)
        """, s)

    # SME tasks
    tasks = [
        ("T-001", "OPP-001", "Alex Mercer", "2026-06-25", "Please confirm if we can use our standard security policy for tenant isolation or if we need to draft a custom RAG tenant isolation architecture.", "REQ-102", "Pending", "We need access to their network diagram first.", "", "Confirm with customer"),
        ("T-002", "OPP-001", "Sarah Connor", "2026-06-20", "Confirm that requirements extraction code handles scanned PDFs correctly.", "REQ-101", "Done", "Yes, tested on sample briefs. Exposes warnings if page text length is below threshold.", "", "Approved"),
    ]
    for t in tasks:
        execute_query("""
        INSERT INTO sme_tasks (id, opportunity_id, assignee, due_date, task_details, related_req_id, status, comments, attachments, decision)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, t)

    # Questionnaire items
    q_items = [
        ("QI-001", "OPP-004", "Does your application encrypt data at rest?", "Yes, we use SQLite local encryption and encrypt all output payloads using AES-256.", 95, "Approved", "security_questionnaire.csv"),
        ("QI-002", "OPP-004", "Where is the data hosted?", "Data is hosted locally on the user's environment. When using cloud LLM providers, data is transmitted over TLS but not stored permanently on their systems.", 80, "Pending", "security_questionnaire.csv"),
        ("QI-003", "OPP-004", "Do you conduct regular penetration testing?", "Yes, we conduct vulnerability scanning and pen-testing semi-annually. Reports are available upon NDA signature.", 90, "Approved", "security_questionnaire.csv"),
    ]
    for q in q_items:
        execute_query("""
        INSERT INTO questionnaire_items (id, opportunity_id, question_text, detected_answer, confidence, status, source_file)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, q)

    # Win loss
    win_loss = [
        ("WL-001", "OPP-003", "Won", "Excellent past performance with RAG systems and fast turnaround (3 weeks).", "DevCorp Solutions", "Apex loved the live interactive demo we showed in Streamlit.", "Competitor price was 32k, we offered 25k.", "High delivery speed, active pre-sales communication.", "None identified.", "Maintain core reusable RAG templates for finance.", "Seeded KB-003 Apex case study.", "Yes, updated pricing assumptions library."),
    ]
    for wl in win_loss:
        execute_query("""
        INSERT INTO win_loss_records (id, opportunity_id, outcome, reason, competitor, buyer_feedback, price_feedback, strengths, weaknesses, lessons_learned, reusable_content, kb_updates)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, wl)

    # Evals
    evals = [
        ("EV-001", "2026-06-15T10:00:00", "Requirement extraction accuracy", 92.5, "Tested using Small RFP Sample. Successfully extracted 18 of 20 mandatory clauses."),
        ("EV-002", "2026-06-15T11:30:00", "Risk detection recall", 88.0, "Correctly identified 9 out of 10 red flags from Gov Cloud Security Questionnaire sample."),
    ]
    for ev in evals:
        execute_query("""
        INSERT INTO eval_runs (id, timestamp, eval_type, accuracy_score, comments)
        VALUES (?, ?, ?, ?, ?)
        """, ev)

    # Audit log
    audit = [
        ("A-001", "OPP-001", "Upload RFP Brief", "PDF file uploaded: RFP_Logistics_Intelligence.pdf (size 2.4 MB)", "Successfully parsed 12 pages, found 4,200 words.", "N/A", "N/A", 0.8, 0, "Success", now_str, "Sarah Connor"),
        ("A-002", "OPP-001", "Analyze requirements", "Triggered deep analysis with primary model.", "Extracted 5 core requirements, generated compliance statuses.", "Gemini", "gemini-2.5-pro", 4.2, 8500, "Success", now_str, "Sarah Connor"),
        ("A-003", "OPP-001", "Draft proposal", "Drafted 3 main sections: Summary, Requirements, Technical approach.", "Created markdown draft output (1,400 words).", "Gemini", "gemini-2.5-pro", 5.1, 12000, "Success", now_str, "Sarah Connor"),
    ]
    for a in audit:
        execute_query("""
        INSERT INTO audit_logs (id, opportunity_id, operation, input_summary, output_summary, provider, model, latency, tokens, status, timestamp, user)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, a)

    print("Seeded database successfully.")
