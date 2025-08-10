import streamlit as st
from backend import EducationAgent
import os
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ---- Google Sheets config ----
SPREADSHEET_ID = "1F5XT-ydRjG_Sy9iqK2610kG96HkBZ2gwuCSGMW3LKbc"
USERS_SHEET_NAME = "EduBot_Users"

def _get_usage_worksheet():
    """Return a gspread worksheet for EduBot_Users using st.secrets creds (robust to secrets format)."""
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
            ws = sh.worksheet(USERS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = sh.sheet1
        return ws

    except Exception as e:
        st.session_state["_usage_ws_error"] = repr(e)
        return None

def _log_user_to_sheets(name: str):
    ts = datetime.utcnow().isoformat() + "Z"
    ws = _get_usage_worksheet()
    if ws is not None:
        try:
            ws.append_row([name, ts], value_input_option="RAW")
            return True, None
        except Exception as e:
            return False, f"Sheets append failed: {e}"
    else:
        return False, f"Sheets not available: {st.session_state.get('_usage_ws_error')}"

# ---- Page Config ----
st.set_page_config(
    page_title="EduBot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---- Responsive CSS ----
def apply_responsive_css():
    st.markdown("""
    <style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.9rem !important;
            padding-right: 0.9rem !important;
            padding-bottom: calc(5rem + env(safe-area-inset-bottom, 0px)) !important;
        }
    }
    :root, .stApp {
        color-scheme: light dark;
    }
    @media (prefers-color-scheme: light) {
        .stApp {
            background: radial-gradient(circle at 1px 1px, rgba(0,0,0,0.06) 1px, transparent 1px);
            background-size: 18px 18px;
            background-color: #f9fafb;
        }
    }
    @media (prefers-color-scheme: dark) {
        .stApp {
            background: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 1px);
            background-size: 18px 18px;
            background-color: #111418;
        }
    }
    .stTextInput input, .stTextArea textarea {
        font-size: 16px !important;
        min-height: 44px;
    }
    @media (max-width: 640px) {
        .stButton>button {
            width: 100%;
            height: 44px;
            font-size: 16px;
        }
    }
    .stChatInput {
        padding-bottom: env(safe-area-inset-bottom, 0px);
    }
    </style>
    """, unsafe_allow_html=True)

apply_responsive_css()

# ---- Background Pattern ----
def set_bg_pattern(style: str = "dots"):
    if style == "dots":
        css = """
        <style>
        .stApp {
            background: radial-gradient(circle at 1px 1px, rgba(0,0,0,0.06) 1px, transparent 1px);
            background-size: 18px 18px;
            background-color: #f9fafb;
        }
        </style>
        """
    elif style == "grid":
        css = """
        <style>
        .stApp {
            background: linear-gradient(rgba(0,0,0,0.035) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(0,0,0,0.035) 1px, transparent 1px);
            background-size: 28px 28px;
            background-color: #fbfdff;
        }
        </style>
        """
    else:
        css = "<style>.stApp { background-color: #fafafa; }</style>"
    st.markdown(css, unsafe_allow_html=True)

set_bg_pattern("dots")

# ---- Onboarding ----
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.onboarded:
    st.markdown("## 👋 Welcome to **AI Education Consultant**")
    st.caption("Enter any username to continue. We only need this to track traffic.")
    with st.form("welcome_form"):
        username_input = st.text_input("Enter your username", value=st.session_state.username)
        submitted = st.form_submit_button("Continue")
    if submitted:
        username_input = username_input.strip()
        if not username_input:
            st.warning("Please enter a valid name.")
            st.stop()
        _log_user_to_sheets(username_input)
        st.session_state.username = username_input
        st.session_state.onboarded = True
        st.rerun()
    st.stop()

st.sidebar.markdown(f"**User:** {st.session_state.username}")

# ---- Initialize Agent ----
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm your education consultant. Tell me about your academic goals."}
    ]

# ---- Title ----
st.title("🎓 EduBot - AI Education Consultant")
st.caption("A platform for career guidance")

# ---- Display Messages ----
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---- Sidebar: Document Upload ----
with st.sidebar:
    st.header("📄 Document Analysis")
    uploaded_file = st.file_uploader("Upload a document", type=["pdf", "txt", "docx", "jpg", "png", "jpeg"])
    doc_type = st.selectbox("Select document type", ["cv", "resume", "transcript", "sop", "motivation letter"])
    st.subheader("🎯 Analysis Lens")
    purpose = st.selectbox("Analyze for", ["Masters admission", "PhD admission", "Job application", "Email to professor"])
    extra_context = st.text_area("Extra context (optional)")
    analyze_clicked = st.button("Analyze Document", type="primary", use_container_width=True)

if uploaded_file and analyze_clicked:
    with st.spinner(f"Analyzing your {doc_type} for “{purpose}”..."):
        try:
            analysis = st.session_state.agent.analyze_document(
                file_bytes=uploaded_file.read(),
                filename=uploaded_file.name,
                doc_type=doc_type,
                purpose=purpose,
                extra_context=extra_context
            )
            extracted_text = analysis.get("text", "")
            feedback = analysis.get("feedback", "")
            enhanced = analysis.get("enhanced_version", "")
            issues = analysis.get("issues", [])

            tabs = st.tabs(["Feedback", "Sections to Fix", "Enhanced Version", "Extracted Text"])
            with tabs[0]:
                st.text_area("Feedback", value=feedback, height=220)
            with tabs[1]:
                if issues:
                    df_issues = pd.DataFrame(issues)
                    st.dataframe(df_issues, use_container_width=True, hide_index=True)
                else:
                    st.info("No specific sections to fix.")
            with tabs[2]:
                st.text_area("Enhanced Version", value=enhanced, height=300)
            with tabs[3]:
                st.text_area("Extracted Text", value=extracted_text, height=200)
        except Exception as e:
            st.error(f"Analysis failed: {e}")

# ---- Chat Input ----
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
                    st.caption("📌 Scholarship summaries are sourced via public RSS feeds.")
            except Exception as e:
                st.error(f"Error generating response: {e}")
                response = "Sorry, I encountered an error."
    st.session_state.messages.append({"role": "assistant", "content": response})
