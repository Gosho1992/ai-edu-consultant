import streamlit as st
from pathlib import Path
import base64

# --- Page Configuration ---
st.set_page_config(
    page_title="EduBot Pro",
    page_icon="🎓",
    layout="wide"
)

# --- Background Styling ---
def set_background_image():
    background_url = "https://raw.githubusercontent.com/Gosho1992/ai-edu-consultant/main/static/backgroundimage.png"
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] > .main {{
            background-image: url('{background_url}');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stAppViewContainer"] > .main::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(255, 255, 255, 0.8);
            z-index: 0;
        }}
        [data-testid="stAppViewContainer"] > .main > div {{
            position: relative;
            z-index: 1;
        }}
        header {{
            background-color: rgba(255, 255, 255, 0.9) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- Set background ---
set_background_image()

# --- Title ---
st.markdown("""
    <h1 style='text-align: center;'>🎓 EduBot Pro</h1>
    <p style='text-align: center;'>Your AI Education Consultant</p>
""", unsafe_allow_html=True)

# --- Chat Container ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Input ---
user_input = st.chat_input("Ask about universities or scholarships...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Placeholder response (to be replaced with backend response)
    assistant_response = "Let me help you with that... (This will be connected to backend)"
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    with st.chat_message("assistant"):
        st.markdown(assistant_response)

# --- File Upload (Below Input Bar) ---
st.markdown("<br>", unsafe_allow_html=True)
with st.container():
    uploaded_file = st.file_uploader(
        "Upload your file (PDF, DOCX, PNG, JPG)",
        type=["pdf", "docx", "png", "jpg", "jpeg"],
        label_visibility="visible"
    )

    if uploaded_file:
        st.success(f"Uploaded: {uploaded_file.name}")
        # To integrate with backend later
