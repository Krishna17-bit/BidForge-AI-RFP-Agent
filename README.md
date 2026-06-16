# BidForge AI — Bid Decision, Compliance, & Proposal Automation Platform

> **BidForge AI** is a production-oriented, local-first opportunity intelligence and proposal automation platform for RFPs, RFIs, RFQs, grants, tender calls, security questionnaires, and client briefs. It operates as an **AI proposal team in a box**, guiding capture managers, freelancers, and pre-sales engineers from intake parsing through compliance validation, RAG groundings, red-team auditing, and package exports.

---

## Why BidForge AI Exists

Most public RFP automation tools focus strictly on static answer-library management or simple chatbot generation. BidForge AI target critical market gaps by handling the **complete bid lifecycle**:
1. **Multi-Workspace Partitioning**: Segment opportunities and assets between different agency, corporate, or freelancer profiles.
2. **Scan-Aware Ingestion**: PDF size validations with OCR scanning fallbacks for image-only documents.
3. **Rigorous Decision Engine**: Calculate fit and risk ratings across 16 capability sliders *before* writing drafts.
4. **Hybrid RAG Evidence Grounding**: Leverage local TF-IDF matrices alongside cloud embeddings (Gemini/OpenAI) to match requirements to past projects.
5. **Git-Like Version Timelines**: Save proposal draft edits, view side-by-side versions, and restore rollbacks from the database.
6. **Programmatic API & Extension**: Query 20+ REST endpoints or use the loadable Chrome helper extension to autofill forms in online procurement portals.

---

## 📂 Folder Structure

```text
bidforge-ai/
├── app.py                     # Streamlit Frontend Web App Dashboard
├── src/
│   ├── config.py              # Configuration Loader & Environment variables
│   ├── database.py            # SQLite persistent database schema and seeding script
│   ├── document_loader.py     # PDF, DOCX, TXT structure text parser
│   ├── ocr.py                 # Scanned PDF/Image OCR scanner pipeline
│   ├── llm_clients.py         # Unified multi-provider LLM adapter with mock engine
│   ├── agents.py              # Agent prompt architectures & DB run tracing
│   ├── orchestrator.py        # Multi-agent workflow coordinator
│   ├── retrieval.py           # Local TF-IDF & dense embeddings retriever
│   ├── schemas.py             # Pydantic structured output models
│   └── api.py                 # FastAPI backend REST application
├── browser-extension/         # Chrome Extension autocompleter helper files
│   ├── manifest.json          # Extension permission manifest
│   ├── popup.html             # Extension selector view layout
│   ├── popup.js               # Extension API connector
│   └── content.js             # Document field autofiller script
├── tests/
│   ├── test_db.py             # SQLite CRUD tests
│   ├── test_scoring.py        # Rating model calculations
│   ├── test_document_loader.py# File validation tests
│   ├── test_api.py            # FastAPI route tests
│   ├── test_ocr.py            # OCR fallback checks
│   └── test_versioning.py     # Proposal version diff restore tests
├── .env.example               # Environment variables template
├── .gitignore                 # Excluded directories filters
├── requirements.txt           # Python package dependencies
└── README.md                  # System documentation
```

---

## 🎨 Architectural Diagrams

### 1. System Architecture

```mermaid
flowchart TD
    classDef client fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px;
    classDef api fill:#f0fdf4,stroke:#166534,stroke-width:2px;
    classDef db fill:#fff1f2,stroke:#9f1239,stroke-width:2px;
    classDef llg fill:#fffbeb,stroke:#92400e,stroke-width:2px;
    
    U[Freelancer / Proposal Team]:::client --> UI[Streamlit UI Dashboard]:::client
    UI --> API[FastAPI Backend Server]:::api
    
    API --> INTAKE[Intake & OCR Module]:::api
    API --> PARSER[RFP Parser]:::api
    API --> REQ[Requirement Extractor]:::api
    API --> MATRIX[Compliance Matrix]:::api
    API --> SCORE[Fit & Risk Engine]:::api
    API --> KB[Evidence Library]:::api
    
    API --> SQL[(SQLite Database)]:::db
    API --> LLG[LLM Gateway Layer]:::llg
    
    LLG --> GEMINI[Gemini]:::llg
    LLG --> OPENAI[OpenAI]:::llg
    LLG --> CLAUDE[Anthropic]:::llg
    LLG --> GROQ[Groq]:::llg
    LLG --> OLLAMA[Ollama]:::llg
    LLG --> MOCK[Smart Mock]:::llg
```

### 2. Full Bid Lifecycle Workflow

```mermaid
flowchart TD
    classDef step fill:#f0fdf4,stroke:#166534,stroke-width:2px;
    classDef choice fill:#fffbeb,stroke:#92400e,stroke-width:2px;
    classDef bad fill:#fff1f2,stroke:#9f1239,stroke-width:2px;
    
    OPP[New RFP / Brief] --> INTAKE[Upload & Parse Ingestion]:::step
    INTAKE --> REQS[Extract Requirements]:::step
    REQS --> COMP[Build Compliance Matrix]:::step
    COMP --> SCORE[Bid / No-Bid Rating]:::step
    SCORE --> DECISION{Bid Decision?}:::choice
    
    DECISION -- No-Bid --> ARCHIVE[Archive and Save Lessons]:::bad
    DECISION -- Bid --> STRATEGY[Define Strategy & Win Themes]:::step
    
    STRATEGY --> BUILD[Proposal Builder Drafting]:::step
    BUILD --> REVIEW[SME & Red-Team Audit Review]:::step
    REVIEW --> EXPORT[Export Submit Package]:::step
    EXPORT --> OUTCOME[Log Win/Loss learnings]:::step
```

### 3. Ingestion & Requirement Extraction

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Streamlit UI
    participant API as FastAPI Backend
    participant AG as Extraction Agent
    participant DB as SQLite DB
    
    User->>UI: Upload RFP doc or paste text
    UI->>API: Send parsing payload
    API->>AG: Process document metadata (size, OCR check)
    AG->>API: Return requirements list with stable IDs
    API->>DB: Save requirements to database
    API-->>UI: Update analysis dashboard
```

### 4. Bid / No-Bid Rating Logic

```mermaid
flowchart LR
    classDef input fill:#f1f5f9,stroke:#475569,stroke-width:2px;
    classDef math fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px;
    classDef decision fill:#fffbeb,stroke:#92400e,stroke-width:2px;
    
    REQ[Requirements complexity]:::input --> FIT[Fit Scoring Engine]:::math
    RISK[Risk Severity]:::input --> FIT
    CAP[Knowledge Base assets]:::input --> FIT
    DEAD[Deadline pressure]:::input --> FIT
    
    FIT --> RECO[Recommended Decision]:::decision
    RECO --> FINAL[Human Decision override]:::decision
```

### 5. Red-Team Review Pipeline

```mermaid
flowchart TD
    classDef green fill:#f0fdf4,stroke:#166534,stroke-width:2px;
    classDef red fill:#fff1f2,stroke:#9f1239,stroke-width:2px;
    classDef yellow fill:#fffbeb,stroke:#92400e,stroke-width:2px;
    
    DRAFT[Proposal Markdown Draft] --> AUDIT[Verify Grounding & Gaps]
    AUDIT --> CHECKS{Reviewer Outcome?}
    
    CHECKS -- Approved --> FINAL[Mark Section Final]:::green
    CHECKS -- Revisions Needed --> EDIT[Edit draft inline]:::yellow
    CHECKS -- Rejected --> REWRITE[AI Rewrite / SME Task]:::red
    
    EDIT --> FINAL
    REWRITE --> AUDIT
```

### 6. Deployment Topology

```mermaid
flowchart TD
    classDef client fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px;
    classDef serv fill:#f0fdf4,stroke:#166534,stroke-width:2px;
    classDef stor fill:#fff1f2,stroke:#9f1239,stroke-width:2px;
    
    DEV[Local / Pre-sales workstation]:::client --> COMB[Docker Container]:::serv
    COMB --> STR[Streamlit Dashboard Web Port 8501]:::serv
    COMB --> FAST[FastAPI Endpoint Port 8000]:::serv
    
    FAST --> SQLite[(sqlite3 File storage)]:::stor
    FAST --> EXPORTS[exports/ Directory]:::stor
```

---

## 🛠️ Setup & Installation

### 1. Python Environment Setup
Install Python 3.9+ and execute the following commands in the project folder:

```bash
# Clone & enter directory
git clone <REPO_URL>
cd bidforge-ai

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Mac/Linux:
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 2. Run the Workspace
```bash
streamlit run app.py
```
This initializes the Streamlit human-in-the-loop dashboard (on port `8501`) and triggers the FastAPI REST endpoints (on port `8000`) simultaneously in the background.

---

## ⚙️ Configuration & Credentials

Setup your `.env` configuration:

```env
APP_MODE=local
MOCK_MODE=true # Toggle false to connect live API keys
LLM_PROVIDER=mock

# Gemini configuration
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# OpenAI configuration
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# Anthropic configuration
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

# Groq configuration
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-70b-versatile
```

If `MOCK_MODE=true` is set, the application operates fully offline. It will dynamically generate mock context, requirement IDs, compliance matrices, and proposal sections based on keywords found inside the briefs.

---

## 📖 Advanced Features Setup

### 1. Scanning with OCR
To parse image-only scanned PDFs, the pipeline uses `tesseract` and `pdf2image`. 
If these system packages are missing, the system will gracefully issue a system notice banner and continue parsing with normal text loaders. To enable OCR:
- **Windows**: Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and add it to your System PATH variables. Download [poppler-windows](http://blog.alivate.com.au/poppler-windows/) and add the `bin/` directory to PATH.
- **Mac**: Run `brew install tesseract poppler`
- **Linux**: Run `sudo apt-get install tesseract-ocr poppler-utils`

### 2. Installing the Chrome Autocompleter Extension
1. Open Google Chrome.
2. Navigate to `chrome://extensions/` and enable **Developer Mode** (top-right toggle).
3. Click **Load unpacked** (top-left button).
4. Select the `browser-extension/` directory inside this repository.
5. Focus any text field in a procurement portal page, open the extension popup, select your active opportunity, and click any RAG compliance answer to auto-fill the form field instantly.

### 3. Git-Like Version Diffs
When editing a proposal draft section under **Proposal Builder**:
- Click **Save Draft Changes** to automatically log the current draft state as a version index.
- Use the **Version Control History** box below the editor to select historic timestamps, compare texts side-by-side, and restore previous versions.

### 4. Hybrid Semantic Retrieval
When API keys for Gemini or OpenAI are configured, the **Evidence Mapping** page automatically queries dense vectors using:
- `text-embedding-004` (Gemini)
- `text-embedding-3-small` (OpenAI)
If API keys are absent or Mock Mode is enabled, the index falls back to sparse TF-IDF vectors, ensuring zero-cost matching runs smoothly.

---

## 🧪 Testing
Run the complete unit and regression test suite:

```bash
python -m pytest
```

---

## 🌐 Backend REST Endpoints
Programmatic interactions are supported via port `8000`. You can inspect the Swagger interface at `http://127.0.0.1:8000/docs`.

#### Python Programmatic Fetch Sample
```python
import requests

# Fetch pipeline opportunities from local sqlite database
response = requests.get("http://127.0.0.1:8000/api/opportunities")
print(response.json())
```

---

## ⚖️ License
Licensed under the [MIT License](LICENSE).
