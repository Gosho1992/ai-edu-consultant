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

# ---- Responsive CSS with iPhone fixes ----
def apply_responsive_css():
    st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* General mobile adjustments */
    @media (max-width: 640px) {
        .block-container {
            padding-left: 0.9rem !important;
            padding-right: 0.9rem !important;
            padding-bottom: calc(5rem + env(safe-area-inset-bottom, 0px)) !important;
        }
        .stButton>button {
            width: 100%;
            height: 48px;
            font-size: 16px;
            padding: 12px 24px;
        }
        .stChatMessage {
            margin: 8px 0;
            padding: 12px 16px;
        }
    }
    
    /* Input fields styling */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        font-size: 16px !important;
        min-height: 44px !important;
        padding: 12px 15px !important;
    }
    
    /* Dark mode fixes */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 1px);
            background-size: 18px 18px;
            background-color: #111418;
        }
        .stMarkdown, .stTextInput label, .stSelectbox label, .stTextArea label,
        .stButton>button, .stChatMessage, .stAlert {
            color: #ffffff !important;
        }
        .stTextInput input, .stTextArea textarea {
            background-color: #2b2b2b !important;
            color: #ffffff !important;
            border-color: #555555 !important;
        }
    }
    
    /* Light mode styling */
    @media (prefers-color-scheme: light) {
        .stApp {
            background: radial-gradient(circle at 1px 1px, rgba(0,0,0,0.06) 1px, transparent 1px);
            background-size: 18px 18px;
            background-color: #f9fafb;
        }
    }
    
    /* iPhone-specific fixes */
    @supports (-webkit-touch-callout: none) {
        .block-container {
            padding-bottom: calc(5rem + env(safe-area-inset-bottom, 0px)) !important;
        }
        .stChatInput {
            padding-bottom: env(safe-area-inset-bottom, 0px) !important;
        }
        .stApp {
            -webkit-font-smoothing: antialiased;
        }
        @viewport {
            width: device-width;
            zoom: 1.0;
        }
    }
    
    /* Chat input bottom padding */
    .stChatInput {
        padding-bottom: env(safe-area-inset-bottom, 0px);
    }
    </style>
    """, unsafe_allow_html=True)

apply_responsive_css()

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
    with st.spinner(f"Analyzing your {doc_type} for '{purpose}'..."):
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
