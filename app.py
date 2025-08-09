import streamlit as st
from backend import EducationAgent
import os
from datetime import datetime
import json

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1F5XT-ydRjG_Sy9iqK2610kG96HkBZ2gwuCSGMW3LKbc"
USERS_SHEET_NAME = "EduBot_Users"

def _get_usage_worksheet():
    """Return a gspread worksheet for EduBot_Users using st.secrets creds."""
    try:
        creds_dict = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(USERS_SHEET_NAME)
        return ws
    except Exception as e:
        # If anything fails, return None; caller may use CSV fallback
        st.session_state["_usage_ws_error"] = str(e)
        return None


def _log_user_to_sheets(name: str):
    """Append [Name, TimestampUTC] to Google Sheets or CSV fallback."""
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


# Set up the app
st.set_page_config(page_title="EduBot", page_icon="🎓")

# ---- Lightweight background pattern (pure CSS) ----
def set_bg_pattern(style: str = "dots"):
    css = ""

    if style == "dots":
        # micro dots on very light background
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
        # faint grid lines
        css = """
        <style>
        .stApp {
            background:
                linear-gradient(rgba(0,0,0,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0,0,0,0.035) 1px, transparent 1px);
            background-size: 28px 28px;
            background-color: #fbfdff;
        }
        </style>
        """

    elif style == "stripes":
        # ultra-subtle diagonal stripes
        css = """
        <style>
        .stApp {
            background: repeating-linear-gradient(
                135deg,
                #fafbfd,
                #fafbfd 14px,
                #f2f5f9 14px,
                #f2f5f9 28px
            );
        }
        </style>
        """

    else:
        # fallback: just a soft solid
        css = """
        <style>
        .stApp { background-color: #fafafa; }
        </style>
        """

    import streamlit as st
    st.markdown(css, unsafe_allow_html=True)

# Choose your pattern here: "dots" | "grid" | "stripes"
set_bg_pattern("dots")


# ---- Onboarding state ----
if "onboarded" not in st.session_state:
    st.session_state.onboarded = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ---- Welcome + username capture ----
if not st.session_state.onboarded:
    st.markdown("## 👋 Welcome to **AI Education Consultant**")
    st.caption("Enter a username to continue. We only log your name and a timestamp in Google Sheets.")

    with st.form("welcome_form", clear_on_submit=False):
        username_input = st.text_input("Your username", value=st.session_state.username, max_chars=50)
        submitted = st.form_submit_button("Continue")

    if submitted:
        username_input = (username_input or "").strip()
        if not username_input:
            st.warning("Please enter a valid name.")
            st.stop()

        ok, err = _log_user_to_sheets(username_input)
        if not ok:
            # Don't block the app—just inform and continue
            st.info("Logged you in, but saving to Google Sheets failed. The app will continue.")
            if err:
                st.caption(f"Details: {err}")

        st.session_state.username = username_input
        st.session_state.onboarded = True
        st.rerun()

    # Stop rendering the rest of the app until username is submitted
    st.stop()

# ---- If we reach here, user is onboarded ----
st.sidebar.markdown(f"**User:** {st.session_state.username}")


# Initialize the agent
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm your education consultant. Tell me about your academic goals."}
    ]

# Title and description
st.title("🎓 EduBot - AI Education Consultant")
st.caption("A ChatGPT-like interface for university guidance")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Document upload section in sidebar
with st.sidebar:
    st.header("📄 Document Analysis")
    uploaded_file = st.file_uploader(
        "Upload your documents for analysis",
        type=["pdf", "txt", "docx", "jpg", "png", "jpeg"],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:
        file_extension = os.path.splitext(uploaded_file.name)[1][1:].lower()
        valid_types = ["cv", "resume", "transcript", "sop", "motivation letter"]
        
        doc_type = st.selectbox(
            "Select document type",
            valid_types,
            index=3 if "sop" in uploaded_file.name.lower() else 
                 0 if "resume" in uploaded_file.name.lower() or "cv" in uploaded_file.name.lower() else
                 1 if "transcript" in uploaded_file.name.lower() else 3
        )
        
        if st.button("Analyze Document"):
            with st.spinner(f"Analyzing your {doc_type}..."):
                try:
                    file_bytes = uploaded_file.read()
                    
                    if len(file_bytes) == 0:
                        st.error("Uploaded file is empty")
                        st.stop()
                    
                    backend_doc_type = "cv" if doc_type in ["resume", "cv"] else doc_type
                    analysis = st.session_state.agent.analyze_document(
                        file_bytes=file_bytes,
                        filename=uploaded_file.name,
                        doc_type=backend_doc_type
                    )
                    
                    if analysis.get("error"):
                        st.error(analysis["error"])
                    else:
                        st.subheader("Analysis Results")
                        
                        if analysis.get("text"):
                            st.text_area("Extracted Text", 
                                       value=analysis["text"], 
                                       height=200,
                                       key="extracted_text")
                        
                        if analysis.get("feedback"):
                            st.text_area("Feedback", 
                                        value=analysis["feedback"], 
                                        height=200,
                                        key="feedback")
                        
                        if backend_doc_type == "sop" and analysis.get("enhanced_version"):
                            st.text_area("Enhanced Version", 
                                        value=analysis["enhanced_version"], 
                                        height=300,
                                        key="enhanced_version")
                
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.error("Please ensure you've uploaded a valid document file.")

# Chat input
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
                    st.markdown(
                        """
                        <div style="margin-top: 1rem; font-size: 0.85rem; color: gray;">
                        📌 <em>Scholarship summaries are sourced via public RSS feeds from ScholarshipsCorner and ScholarshipUnion. For complete details, always refer to the original websites.</em>
                        </div>
                        """, unsafe_allow_html=True
                    )
                
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
                response = "Sorry, I encountered an error. Please try again."
        
    st.session_state.messages.append({"role": "assistant", "content": response})

