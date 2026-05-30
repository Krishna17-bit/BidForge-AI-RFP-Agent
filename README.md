# BidForge AI — Multi-Agent RFP / Proposal Intelligence Agent

BidForge AI is a polished, local-first RFP analysis and proposal drafting workspace for freelancers, small agencies, AI consultants, and technical service teams.

It turns an uploaded RFP, tender, Upwork job post, or client brief into:

- Bid / no-bid recommendation
- Bid score and proposal quality score
- Requirement extraction
- Evidence-linked compliance matrix
- Risk register
- Clarifying questions
- Solution architecture
- Delivery plan
- Pricing assumptions
- Client-ready proposal draft
- DOCX, Markdown, JSON, and CSV exports

The UI does **not** expose LLM/provider controls. Configure keys in `.env` only.

---

## Why this project 

Most public RFP demos are generic proposal writers. This project is different because it includes:

1. Multi-agent bid strategy workflow
2. Requirement extraction with stable IDs
3. Local evidence retrieval over uploaded RFP + capability documents
4. Compliance matrix with confidence and response strategy
5. Risk and assumptions review
6. Solution architecture and delivery planning
7. Proposal drafting plus reviewer quality gate
8. Exportable client-facing deliverables
9. Gemini-first execution with Groq fallback

---

## Tech stack

- Python
- Streamlit
- Gemini API via `google-genai`
- Groq fallback via `groq`
- TF-IDF retrieval for local evidence mapping
- pypdf and python-docx for document extraction/export
- pandas/scikit-learn for matrix and retrieval utilities

---

## Setup 

### 1. Unzip and open folder

```bash
cd rfp_bid_intelligence_agent
```

### 2. Create virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Mac/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add API keys

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-pro
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Gemini is tried first. Groq is used only if Gemini is unavailable or fails.

### 5. Run app

```bash
streamlit run app.py
```

Open the local URL shown in the terminal.

---

## Demo flow

1. Turn on **Use sample demo brief** in the sidebar.
2. Keep the default sample company profile.
3. Click **Analyze opportunity**.
4. Review the dashboard tabs:
   - Compliance
   - Risks
   - Architecture
   - Proposal
   - Evidence
   - Exports
5. Download DOCX / Markdown / JSON / CSV outputs.

---

## Using your own client brief

Upload or paste:

- RFP PDF
- Tender document
- Upwork/job post
- Client scope document
- Meeting notes
- Security questionnaire
- Procurement document

Optional evidence documents:

- Case studies
- Portfolio notes
- Service brochure
- Security policy
- Past proposal snippets
- Capability statement

The agent uses these evidence documents to avoid unsupported claims.

---

## Important safety note

This tool drafts and analyzes proposals. You should still manually review outputs before sending anything to a client. The tool is designed to flag missing evidence and uncertainty, but final business commitments, pricing, legal claims, and compliance statements require human approval.

---
