from __future__ import annotations

from pathlib import Path
import json
import tempfile
import zipfile

import pandas as pd
import streamlit as st

from src.document_loader import LoadedDocument, load_uploaded_file, load_path
from src.orchestrator import BidOrchestrator
from src.exporter import compliance_dataframe, risk_dataframe, markdown_report, save_all_outputs
from src.utils import now_slug, safe_filename

APP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = APP_DIR / "outputs"
SAMPLE_RFP = APP_DIR / "sample_data" / "sample_ai_rfp.txt"
SAMPLE_PROFILE = APP_DIR / "sample_data" / "sample_company_profile.txt"

st.set_page_config(
    page_title="BidForge AI | RFP Intelligence Agent",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
  --bg: #050505;
  --panel: #0f0f0f;
  --panel2: #171717;
  --text: #f5f5f5;
  --muted: #b8b8b8;
  --soft: #d8d8d8;
  --border: #2a2a2a;
  --accent: #ff4b5c;
}

html, body, [class*="css"] { color: var(--text) !important; }
.stApp { background: var(--bg) !important; color: var(--text) !important; }
.block-container { padding-top: 3.2rem; max-width: 1220px; }
[data-testid="stHeader"] { background: rgba(5,5,5,.88) !important; backdrop-filter: blur(10px); }
[data-testid="stToolbar"] { color: #f5f5f5 !important; }
[data-testid="stSidebar"] { background: #080808 !important; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] * { color: #f2f2f2 !important; }

h1, h2, h3 { letter-spacing: -0.04em; color: #ffffff !important; }
p, li, div, span, label { color: #e8e8e8; }
small, .small-muted { color: var(--muted) !important; font-size: 0.92rem; }
hr { border-color: var(--border) !important; }

.hero {
  border: 1px solid var(--border);
  border-radius: 28px;
  padding: 30px 34px;
  background: radial-gradient(circle at top left, #191919 0%, #0b0b0b 36%, #050505 100%);
  box-shadow: 0 20px 70px rgba(0,0,0,.45);
  margin-bottom: 18px;
}
.hero-title { font-size: 3.1rem; font-weight: 850; line-height: .95; color: #fff !important; }
.hero-sub { color: #cfcfcf !important; max-width: 920px; font-size: 1.04rem; margin-top: 12px; }
.card {
  border: 1px solid var(--border);
  border-radius: 22px;
  padding: 20px;
  background: var(--panel);
  box-shadow: 0 14px 40px rgba(0,0,0,.28);
}
.metric-card {
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 18px;
  background: #0c0c0c;
}
.metric-label { color: var(--muted) !important; font-size: .78rem; text-transform: uppercase; letter-spacing: .12em; }
.metric-value { color: white !important; font-size: 1.45rem; font-weight: 800; margin-top: 4px; }
.badge, .evidence-pill {
  display: inline-block;
  padding: 6px 10px;
  border: 1px solid #3a3a3a;
  border-radius: 999px;
  color: #f7f7f7 !important;
  background: #111;
  font-size: .78rem;
  margin-right: 6px;
}
.evidence-pill { padding: 3px 8px; color: #050505 !important; background: #f3f3f3; border-color: #f3f3f3; font-size: .72rem; font-weight: 800; }

/* Inputs */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"],
.stMultiSelect div[data-baseweb="select"] {
  background: #101010 !important;
  border: 1px solid #353535 !important;
  color: #ffffff !important;
  caret-color: #ffffff !important;
  border-radius: 12px !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
  color: #9a9a9a !important;
  opacity: 1 !important;
}
.stSelectbox div[data-baseweb="select"] *,
.stMultiSelect div[data-baseweb="select"] * {
  color: #ffffff !important;
}
.stSelectbox svg, .stMultiSelect svg { fill: #ffffff !important; color: #ffffff !important; }

/* Dropdown menu rendered in portal */
div[data-baseweb="popover"], div[data-baseweb="menu"] {
  background: #111111 !important;
  border: 1px solid #333333 !important;
  color: #ffffff !important;
}
ul[role="listbox"], [role="listbox"] {
  background: #111111 !important;
  border: 1px solid #333333 !important;
  color: #ffffff !important;
}
li[role="option"], [role="option"] {
  background: #111111 !important;
  color: #ffffff !important;
}
li[role="option"] *, [role="option"] * { color: #ffffff !important; }
li[role="option"]:hover, [role="option"]:hover,
li[aria-selected="true"], [aria-selected="true"] {
  background: #242424 !important;
  color: #ffffff !important;
}

/* Buttons: no more white/grey unreadable labels */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFileUploader"] button {
  border-radius: 14px !important;
  border: 1px solid #4a4a4a !important;
  background: #151515 !important;
  color: #ffffff !important;
  font-weight: 750 !important;
  padding: .65rem 1rem !important;
  box-shadow: none !important;
}
.stButton > button *,
.stDownloadButton > button *,
[data-testid="stFileUploader"] button * {
  color: #ffffff !important;
  fill: #ffffff !important;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFileUploader"] button:hover {
  border-color: #ffffff !important;
  background: #242424 !important;
  color: #ffffff !important;
}
.stButton > button:disabled,
.stDownloadButton > button:disabled,
[data-testid="stFileUploader"] button:disabled {
  background: #191919 !important;
  color: #9d9d9d !important;
  border-color: #333333 !important;
  opacity: 1 !important;
}
.stButton > button:disabled *,
.stDownloadButton > button:disabled *,
[data-testid="stFileUploader"] button:disabled * { color: #9d9d9d !important; }

/* File uploader contrast */
[data-testid="stFileUploader"] section {
  background: #0f0f0f !important;
  border: 1px dashed #3a3a3a !important;
  border-radius: 18px !important;
}
[data-testid="stFileUploader"] section * { color: #dedede !important; }
[data-testid="stFileUploaderFile"] { background: #141414 !important; border: 1px solid #2f2f2f !important; }
[data-testid="stFileUploaderFile"] * { color: #ffffff !important; }

/* Tabs, expanders, captions, alerts */
.stTabs [data-baseweb="tab"] { color: #cfcfcf !important; font-weight: 700 !important; }
.stTabs [aria-selected="true"] { color: #ffffff !important; }
[data-testid="stExpander"] { border: 1px solid #2a2a2a !important; background: #0d0d0d !important; border-radius: 14px !important; }
[data-testid="stExpander"] * { color: #e8e8e8 !important; }
[data-testid="stCaptionContainer"] * { color: #bdbdbd !important; }
.stAlert * { color: #ffffff !important; }

/* Dataframes */
[data-testid="stDataFrame"] { border: 1px solid #252525; border-radius: 12px; }
[data-testid="stDataFrame"] * { color: #f2f2f2 !important; }

/* Markdown code chips used for win themes */
code {
  color: #f0f0f0 !important;
  background: #171717 !important;
  border: 1px solid #2d2d2d !important;
  border-radius: 8px !important;
  padding: 3px 7px !important;
}
</style>
""",
    unsafe_allow_html=True,
)


def load_docs_from_uploads(files) -> list[LoadedDocument]:
    docs = []
    for f in files or []:
        try:
            docs.append(load_uploaded_file(f))
        except Exception as exc:
            st.error(f"Could not load {getattr(f, 'name', 'file')}: {exc}")
    return docs


def make_zip(paths: dict[str, Path]) -> bytes:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for label, path in paths.items():
            zf.write(path, arcname=path.name)
    data = Path(tmp.name).read_bytes()
    Path(tmp.name).unlink(missing_ok=True)
    return data


def status_counts(df: pd.DataFrame) -> dict[str, int]:
    if df.empty or "Status" not in df.columns:
        return {}
    return df["Status"].value_counts().to_dict()


st.markdown(
    """
<div class="hero">
  <div class="badge">RFP Intelligence</div><div class="badge">Compliance Matrix</div><div class="badge">Proposal Draft</div><div class="badge">Risk Review</div>
  <div class="hero-title">BidForge AI</div>
  <div class="hero-sub">A local-first multi-agent workspace for turning RFPs, tenders, job posts, and client briefs into evidence-backed bid decisions, technical delivery plans, and polished proposal drafts.</div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Workspace")
    demo_mode = st.toggle("Use sample demo brief", value=False)
    depth = st.selectbox("Analysis depth", ["Deep", "Standard", "Fast"], index=0)
    tone = st.selectbox(
        "Proposal tone",
        [
            "Consultative, confident, concise",
            "Enterprise and formal",
            "Freelance-friendly and direct",
            "Technical and architecture-heavy",
        ],
        index=0,
    )
    st.markdown("---")
    st.markdown("### Company capability profile")
    default_profile = SAMPLE_PROFILE.read_text(encoding="utf-8") if demo_mode and SAMPLE_PROFILE.exists() else ""
    company_profile = st.text_area(
        "Paste your company/freelancer profile, case studies, capabilities, tools, domains, delivery strengths, pricing rules, or constraints.",
        value=default_profile,
        height=220,
        placeholder="Example: AI/ML engineer with RAG agents, workflow automation, FastAPI/Streamlit, OCR, PDF extraction, cloud deployment...",
    )
    st.markdown("<div class='small-muted'>Tip: Add capability docs below for stronger compliance evidence.</div>", unsafe_allow_html=True)

col_left, col_right = st.columns([1.05, 0.95], gap="large")

with col_left:
    st.markdown("### 1. Add opportunity documents")
    rfp_uploads = st.file_uploader(
        "Upload RFP / tender / job post / project brief",
        type=["pdf", "docx", "txt", "md", "csv"],
        accept_multiple_files=True,
    )
    pasted_brief = st.text_area(
        "Or paste a brief directly",
        height=190,
        placeholder="Paste client brief, Upwork job post, tender scope, or RFP section here...",
    )

with col_right:
    st.markdown("### 2. Add evidence documents")
    knowledge_uploads = st.file_uploader(
        "Upload capability docs / case studies / service brochure / security policy",
        type=["pdf", "docx", "txt", "md", "csv"],
        accept_multiple_files=True,
    )
    st.markdown(
        """
<div class="card">
  <b>What this agent produces</b><br><br>
  <span class="small-muted">• Bid / no-bid score<br>• Requirement extraction<br>• Evidence-linked compliance matrix<br>• Risk register and missing questions<br>• Solution architecture<br>• Milestone plan and pricing assumptions<br>• Proposal draft<br>• Quality reviewer notes<br>• DOCX / Markdown / JSON / CSV exports</span>
</div>
""",
        unsafe_allow_html=True,
    )

run = st.button("Analyze opportunity", use_container_width=True)

if run:
    rfp_docs: list[LoadedDocument] = []
    knowledge_docs: list[LoadedDocument] = []

    if demo_mode and SAMPLE_RFP.exists():
        rfp_docs.append(load_path(SAMPLE_RFP))
    rfp_docs.extend(load_docs_from_uploads(rfp_uploads))
    knowledge_docs.extend(load_docs_from_uploads(knowledge_uploads))

    if pasted_brief.strip():
        rfp_docs.append(LoadedDocument(name="pasted_brief.txt", text=pasted_brief.strip(), pages=[{"page": 1, "text": pasted_brief.strip()}]))

    if not rfp_docs:
        st.warning("Please upload or paste at least one RFP, tender, job post, or project brief.")
        st.stop()

    progress = st.status("Starting bid analysis...", expanded=True)

    def update(msg: str):
        progress.write(msg)

    orchestrator = BidOrchestrator()
    with st.spinner("Analyzing..."):
        bundle = orchestrator.run(
            rfp_docs=rfp_docs,
            knowledge_docs=knowledge_docs,
            company_profile=company_profile,
            depth=depth,
            tone=tone,
            progress_callback=update,
        )
    progress.update(label="Analysis complete", state="complete", expanded=False)
    st.session_state["bundle"] = bundle

    slug = safe_filename(bundle.get("project_title", "rfp_analysis"))[:40] + "_" + now_slug()
    paths = save_all_outputs(bundle, OUTPUT_DIR, slug)
    st.session_state["output_paths"] = {k: str(v) for k, v in paths.items()}

bundle = st.session_state.get("bundle")
if bundle:
    st.markdown("---")
    st.markdown("## Analysis dashboard")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Recommendation</div><div class='metric-value'>{bundle.get('bid_recommendation','Needs More Info')}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Bid score</div><div class='metric-value'>{bundle.get('bid_score','N/A')}/100</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Quality score</div><div class='metric-value'>{bundle.get('quality_score','N/A')}/100</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Requirements</div><div class='metric-value'>{len(bundle.get('requirements',[]) or [])}</div></div>", unsafe_allow_html=True)

    st.markdown("### Opportunity summary")
    st.write(bundle.get("opportunity_summary", ""))

    st.markdown("### Win themes")
    st.write("  ".join([f"`{x}`" for x in bundle.get("win_themes", []) or []]))

    tabs = st.tabs(["Compliance", "Risks", "Architecture", "Proposal", "Evidence", "Exports"])

    with tabs[0]:
        df = compliance_dataframe(bundle)
        counts = status_counts(df)
        if counts:
            st.caption("Status counts: " + " | ".join([f"{k}: {v}" for k, v in counts.items()]))
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[1]:
        rdf = risk_dataframe(bundle)
        st.dataframe(rdf, use_container_width=True, hide_index=True)
        st.markdown("#### Clarifying questions")
        for q in bundle.get("clarifying_questions", []) or []:
            st.markdown(f"- {q}")

    with tabs[2]:
        st.markdown("#### Solution architecture")
        st.write(bundle.get("solution_architecture", ""))
        st.markdown("#### Delivery plan")
        st.dataframe(pd.DataFrame(bundle.get("delivery_plan", []) or []), use_container_width=True, hide_index=True)
        st.markdown("#### Pricing assumptions")
        for a in bundle.get("pricing_assumptions", []) or []:
            st.markdown(f"- {a}")

    with tabs[3]:
        st.markdown(bundle.get("proposal_draft", ""))
        st.markdown("#### Reviewer notes")
        for n in bundle.get("reviewer_notes", []) or []:
            st.markdown(f"- {n}")

    with tabs[4]:
        evidence_pack = bundle.get("evidence_pack", {}) or {}
        for rid, evidence in evidence_pack.items():
            with st.expander(f"Evidence for {rid} ({len(evidence)} chunks)"):
                for item in evidence:
                    label = item.get("evidence_type", "Evidence")
                    st.markdown(
                        f"<span class='evidence-pill'>{label}</span> "
                        f"**{item.get('document')} — page {item.get('page')} — score {item.get('score')}**",
                        unsafe_allow_html=True,
                    )
                    st.write(item.get("text", ""))

    with tabs[5]:
        output_paths = {k: Path(v) for k, v in (st.session_state.get("output_paths") or {}).items()}
        if output_paths:
            st.markdown("Download generated outputs:")
            d1, d2, d3, d4, d5 = st.columns(5)
            with d1:
                st.download_button("Markdown", output_paths["markdown"].read_bytes(), file_name=output_paths["markdown"].name)
            with d2:
                st.download_button("DOCX", output_paths["docx"].read_bytes(), file_name=output_paths["docx"].name)
            with d3:
                st.download_button("JSON", output_paths["json"].read_bytes(), file_name=output_paths["json"].name)
            with d4:
                st.download_button("CSV", output_paths["csv"].read_bytes(), file_name=output_paths["csv"].name)
            with d5:
                st.download_button("All outputs ZIP", make_zip(output_paths), file_name="bidforge_outputs.zip")
        else:
            st.code(markdown_report(bundle)[:5000])
else:
    st.markdown("---")
    st.markdown("### Market-gap positioning")
    st.markdown(
        """
<div class="card">
Most RFP tools are built for enterprise proposal departments with large answer libraries. This demo is positioned differently: it gives small AI/software agencies and freelancers an NDA-safe bid analyst that can read a client brief, identify the actual work, expose hidden risk, map evidence, and produce a polished first proposal without showing model/provider controls in the client-facing UI.
</div>
""",
        unsafe_allow_html=True,
    )
