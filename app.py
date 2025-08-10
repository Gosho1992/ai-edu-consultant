import streamlit as st
from backend import EducationAgent
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# ========= Google Sheets =========
SPREADSHEET_ID = "1F5XT-ydRjG_Sy9iqK2610kG96HkBZ2gwuCSGMW3LKbc"
USERS_SHEET_NAME = "EduBot_Users"

def _get_usage_worksheet():
    """Robust Google Sheets worksheet access with error handling."""
    try:
        raw = st.secrets.get("gcp_service_account")
        if raw is None:
            raise RuntimeError("Missing 'gcp_service_account' in Streamlit secrets.")
        creds_dict = json.loads(raw) if isinstance(raw, str) else dict(raw)

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)

        sheet_id = st.secrets.get("SPREADSHEET_ID", SPREADSHEET_ID)
        sh = gc.open_by_key(sheet_id)
        try:
            return sh.worksheet(USERS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            return sh.sheet1
    except Exception as e:
        st.session_state["_usage_ws_error"] = repr(e)
        return None

def _log_user_to_sheets(name: str):
    """Append [Name, TimestampUTC] to Google Sheets (with graceful fallback)."""
    ts = datetime.utcnow().isoformat() + "Z"
    ws = _get_usage_worksheet()
    if ws is not None:
        try:
            ws.append_row([name, ts], value_input_option="RAW")
            return True, None
        except Exception as e:
            return False, f"Sheets append failed: {e}"
    return False, f"Sheets not available: {st.session_state.get('_usage_ws_error')}"

# ========= Page config =========
st.set_page_config(
    page_title="EduBot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ========= Responsive CSS (safe to all devices) =========
def apply_responsive_css():
    st.markdown(
        """
<style>
/* Layout paddings */
.block-container{
  padding-top:1.25rem;
  padding-bottom:5rem; /* keep content above chat input */
  padding-left:2rem;
  padding-right:2rem;
}
@media (max-width:640px){
  .block-container{
    padding-left:0.9rem !important;
    padding-right:0.9rem !important;
    padding-bottom:calc(5rem + env(safe-area-inset-bottom,0px)) !important;
  }
  .stButton > button{
    width:100%;
    height:44px;
    font-size:16px;
  }
}

/* Respect Streamlit theme for backgrounds */
.stApp[data-base-theme="light"]{
  background:radial-gradient(circle at 1px 1px, rgba(0,0,0,0.06) 1px, transparent 1px);
  background-size:18px 18px;
  background-color:#f9fafb;
}
.stApp[data-base-theme="dark"]{
  background:radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 1px);
  background-size:18px 18px;
  background-color:#0f1115;
}

/* Inputs readable + avoid iOS auto zoom */
.stTextInput input, .stTextArea textarea{
  font-size:16px !important;
  min-height:44px;
}

/* Chat input safe-area on iOS */
.stChatInput{ padding-bottom:env(safe-area-inset-bottom,0px); }

/* Sidebar robust scroll */
aside[data-testid="stSidebar"]{ overflow-y:auto !important; }
</style>
        """,
        unsafe_allow_html=True,
    )

apply_responsive_css()

# ========= Onboarding =========
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.onboarded:
    st.markdown("## 👋 Welcome to **AI Education Consultant**")
    st.caption("Enter any username to continue. We only need this to track traffic.")
    with st.form("welcome_form", clear_on_submit=False):
        username_input = st.text_input(
            "Enter your username",
            value=st.session_state.username,
            max_chars=50,
            placeholder="e.g., Zain",
            help="We only save name + timestamp to count unique users.",
        )
        submitted = st.form_submit_button("Continue")

    if submitted:
        username_input = (username_input or "").strip()
        if not username_input:
            st.warning("Please enter a valid name.")
            st.stop()
        ok, err = _log_user_to_sheets(username_input)
        if not ok:
            st.info("Logged you in, but saving to Google Sheets failed. The app will continue.")
            if err:
                st.caption(f"Details: {err}")
        st.session_state.username = username_input
        st.session_state.onboarded = True
        st.rerun()

    st.stop()

# ========= Sidebar badge =========
st.sidebar.markdown(f"**User:** {st.session_state.username}")

# ========= Agent =========
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm your education consultant. Tell me about your academic goals."}
    ]

# ========= Main UI =========
st.title("🎓 EduBot - AI Education Consultant")
st.caption("A platform for career guidance")

# Chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ========= Sidebar: Document Analysis =========
with st.sidebar:
    st.header("📄 Document Analysis")
    uploaded_file = st.file_uploader(
        "Upload a document",
        type=["pdf", "txt", "docx", "jpg", "png", "jpeg"],
        accept_multiple_files=False,
    )

    # Set default doc type based on filename if possible
    candidates = ["cv", "resume", "transcript", "sop", "motivation letter"]
    default_idx = 0
    if uploaded_file:
        name = uploaded_file.name.lower()
        if "sop" in name:
            default_idx = 3
        elif ("resume" in name) or ("cv" in name):
            default_idx = 0
        elif "transcript" in name:
            default_idx = 2

    doc_type = st.selectbox("Select document type", candidates, index=default_idx)

    st.subheader("🎯 Analysis Lens")
    purpose = st.selectbox(
        "Analyze for",
        ["Masters admission", "PhD admission", "Job application", "Email to professor"],
        index=0,
    )
    extra_context = st.text_area(
        "Extra context (optional)",
        placeholder="e.g., Job title + a few key requirements, target program link, professor's research area URL...",
        height=90,
    )

    analyze_clicked = st.button("Analyze Document", type="primary", use_container_width=True)

# ========= Analysis Results =========
if uploaded_file and analyze_clicked:
    with st.spinner(f"Analyzing your {doc_type} for “{purpose}”..."):
        try:
            analysis = st.session_state.agent.analyze_document(
                file_bytes=uploaded_file.read(),
                filename=uploaded_file.name,
                doc_type=("cv" if doc_type in ["cv", "resume"] else doc_type),
                purpose=purpose,
                extra_context=extra_context,
            )

            if analysis.get("error"):
                st.error(analysis["error"])
            else:
                extracted_text = analysis.get("text") or ""
                feedback = analysis.get("feedback") or ""
                enhanced = analysis.get("enhanced_version") or ""
                issues = analysis.get("issues") or []

                tabs = st.tabs(["Feedback", "Sections to Fix", "Enhanced Version", "Extracted Text"])

                with tabs[0]:
                    if feedback.strip():
                        st.text_area("Feedback", value=feedback, height=220, label_visibility="collapsed")
                    else:
                        st.info("No feedback returned.")

                with tabs[1]:
                    if issues:
                        # Normalize possible issue dicts
                        norm_rows = []
                        for it in issues:
                            it = it or {}
                            norm_rows.append({
                                "Excerpt": it.get("excerpt", ""),
                                "Issue": it.get("issue", ""),
                                "Suggested fix": it.get("suggested_fix", ""),
                            })
                        df_issues = pd.DataFrame(norm_rows, columns=["Excerpt", "Issue", "Suggested fix"])
                        st.dataframe(df_issues, use_container_width=True, hide_index=True)
                    else:
                        st.info("No specific sections to fix were returned.")

                with tabs[2]:
                    if enhanced.strip():
                        st.text_area("Enhanced Version", value=enhanced, height=300, label_visibility="collapsed")
                    else:
                        st.info("No enhanced version returned.")

                with tabs[3]:
                    if extracted_text.strip():
                        st.text_area("Extracted Text", value=extracted_text, height=200, label_visibility="collapsed")
                    else:
                        st.info("No extracted text returned.")
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")

# ========= Chat =========
if prompt := st.chat_input("Ask me about universities or scholarships..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.agent.generate_response(prompt)
                st.markdown(response)
                if "scholarship" in prompt.lower():
                    st.caption("📌 Scholarship summaries are sourced via public RSS feeds. For complete details, see original sites.")
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
                response = "Sorry, I encountered an error. Please try again."

    st.session_state.messages.append({"role": "assistant", "content": response})
