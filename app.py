import streamlit as st
from backend import EducationAgent
import os
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

# ---- Google Sheets config ----
SPREADSHEET_ID = "1F5XT-ydRjG_Sy9iqK2610kG96HkBZ2gwuCSGMW3LKbc"
USERS_SHEET_NAME = "EduBot_Users"

def _get_usage_worksheet():
    """Return a gspread worksheet for EduBot_Users using st.secrets creds (robust to secrets format)."""
    try:
        # 1) Load creds from secrets (supports dict or JSON string)
        raw = st.secrets.get("gcp_service_account")
        if raw is None:
            raise RuntimeError("Missing 'gcp_service_account' in Streamlit secrets.")
        creds_dict = json.loads(raw) if isinstance(raw, str) else dict(raw)

        # 2) Authorize
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)

        # 3) Open spreadsheet (allow override via secrets if present)
        sheet_id = st.secrets.get("SPREADSHEET_ID", SPREADSHEET_ID)
        sh = gc.open_by_key(sheet_id)

        # 4) Get worksheet by name, fallback to first sheet if not found
        try:
            ws = sh.worksheet(USERS_SHEET_NAME)
        except gspread.WorksheetNotFound:
            ws = sh.sheet1  # fallback
        return ws

    except Exception as e:
        st.session_state["_usage_ws_error"] = repr(e)
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


# ---- Page + responsive/mobile CSS (add near the top) ----
st.set_page_config(
    page_title="EduBot",
    page_icon="🎓",
    layout="wide",                       # more breathing room on mobile
    initial_sidebar_state="collapsed"    # sidebar starts hidden on phones
)

def apply_responsive_css():
    st.markdown("""
    <style>
    /* Base container paddings (desktop vs mobile) */
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 5rem; /* keep content above chat input */
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

    /* Ensure text is readable in both themes */
    :root, .stApp {
        color-scheme: light dark;
    }
    /* Light mode subtle dot grid */
    @media (prefers-color-scheme: light) {
        .stApp {
            background: radial-gradient(circle at 1px 1px, rgba(0,0,0,0.06) 1px, transparent 1px);
            background-size: 18px 18px;
            background-color: #f9fafb;
        }
    }
    /* Dark mode: higher contrast but still subtle */
    @media (prefers-color-scheme: dark) {
        .stApp {
            background:
                radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 1px);
            background-size: 18px 18px;
            background-color: #111418;
        }
    }

    /* Inputs: visible label/placeholder + 16px font to stop mobile auto-zoom */
    label, .stMarkdown p, .stCaption {
        line-height: 1.4;
    }
    .stTextInput input, .stTextArea textarea {
        font-size: 16px !important;
        min-height: 44px;        /* touch target */
    }
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        opacity: .75;
    }

    /* Buttons: full-width on mobile for easier tapping */
    @media (max-width: 640px) {
        .stButton>button {
            width: 100%;
            height: 44px;
            font-size: 16px;
        }
    }

    /* Chat input: keep it clear of Android/iOS bottom bars */
    .stChatInput {
        padding-bottom: env(safe-area-inset-bottom, 0px);
    }

    /* Sidebar: make sure controls don’t overflow on small screens */
    section[data-testid="stSidebar"] .css-1d391kg {  /* selector fallback */
        overflow-y: auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_responsive_css()


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
    st.caption("Enter any username to continue. We only need this to track traffic.")

    with st.form("welcome_form", clear_on_submit=False):
        username_input = st.text_input(
            "Enter your username",
            value=st.session_state.username,
            max_chars=50,
            placeholder="e.g., Zain",
            help="We only save name + timestamp to count unique users."
        )
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
st.caption("A platform for career guidance")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Document upload section in sidebar
# Document upload + purpose-aware lens in sidebar
with st.sidebar:
    st.header("📄 Document Analysis")

    uploaded_file = st.file_uploader(
        "Upload a document",
        type=["pdf", "txt", "docx", "jpg", "png", "jpeg"],
        accept_multiple_files=False
    )

    # Document type
    valid_types = ["cv", "resume", "transcript", "sop", "motivation letter"]
    default_idx = (
        3 if (uploaded_file and "sop" in uploaded_file.name.lower())
        else 0 if (uploaded_file and ("resume" in uploaded_file.name.lower() or "cv" in uploaded_file.name.lower()))
        else 1 if (uploaded_file and "transcript" in uploaded_file.name.lower())
        else 0
    )
    doc_type = st.selectbox("Select document type", valid_types, index=default_idx)

    st.divider()

    # 🔎 Analysis Lens (purpose-aware)
    st.subheader("🎯 Analysis Lens")
    purpose = st.selectbox(
        "Analyze for",
        ["Masters admission", "PhD admission", "Job application", "Email to professor"],
        index=0
    )
    extra_context = st.text_area(
        "Extra context (optional)",
        placeholder="e.g., Job title + a few key requirements, target program link, professor's research area URL...",
        height=90
    )

    analyze_clicked = st.button("Analyze Document", type="primary", use_container_width=True)

# Main panel - results
if uploaded_file is not None and analyze_clicked:
    with st.spinner(f"Analyzing your {doc_type} for “{purpose}”..."):
        try:
            file_bytes = uploaded_file.read()
            if not file_bytes:
                st.error("Uploaded file is empty")
                st.stop()

            backend_doc_type = "cv" if doc_type in ["resume", "cv"] else doc_type

            # ⤵️ Pass the new purpose/context to backend (backend will be updated next step)
            analysis = st.session_state.agent.analyze_document(
                file_bytes=file_bytes,
                filename=uploaded_file.name,
                doc_type=backend_doc_type,
                purpose=purpose,
                extra_context=extra_context
            )

            if analysis.get("error"):
                st.error(analysis["error"])
            else:
                # Safely normalize expected fields
                extracted_text = analysis.get("text") or ""
                feedback = analysis.get("feedback") or ""
                enhanced = analysis.get("enhanced_version") or ""
                issues = analysis.get("issues") or []  # expect list of {excerpt, issue, suggested_fix}

                st.subheader("Results")

                # 🧭 Tabs for cleaner UX
                tabs = st.tabs(["Feedback", "Sections to Fix", "Enhanced Version", "Extracted Text"])

                with tabs[0]:
                    if feedback.strip():
                        st.text_area("Feedback", value=feedback, height=220, key="feedback_area", label_visibility="collapsed")
                    else:
                        st.info("No feedback returned.")

                with tabs[1]:
                    # Build a lightweight, readable table for issues
                    if isinstance(issues, list) and len(issues) > 0:
                        # Normalize rows to avoid KeyErrors
                        rows = []
                        for it in issues:
                            rows.append({
                                "Excerpt": (it or {}).get("excerpt", ""),
                                "Issue": (it or {}).get("issue", ""),
                                "Suggested fix": (it or {}).get("suggested_fix", "")
                            })
                        # Use dataframe for nice sticky headers & sorting
                        import pandas as pd
                        df_issues = pd.DataFrame(rows, columns=["Excerpt", "Issue", "Suggested fix"])
                        st.dataframe(df_issues, use_container_width=True, hide_index=True)
                    else:
                        st.info("No specific sections to fix were returned.")

                with tabs[2]:
                    if enhanced.strip():
                        st.text_area("Enhanced Version", value=enhanced, height=300, key="enhanced_area", label_visibility="collapsed")
                    else:
                        st.info("No enhanced version returned.")

                with tabs[3]:
                    if extracted_text.strip():
                        st.text_area("Extracted Text", value=extracted_text, height=200, key="extracted_area", label_visibility="collapsed")
                    else:
                        st.info("No extracted text returned.")

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
                        📌 <em>Scholarship summaries are sourced via public RSS feeds. For complete details, always refer to the original websites.</em>
                        </div>
                        """, unsafe_allow_html=True
                    )
                
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
                response = "Sorry, I encountered an error. Please try again."
        
    st.session_state.messages.append({"role": "assistant", "content": response})









