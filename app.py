import streamlit as st
from streamlit.components.v1 import html
import base64
import requests

# ====== 1. BACKGROUND IMAGE SETUP ====== #
def set_background_image():
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: url("https://raw.githubusercontent.com/Gosho1992/ai-edu-consultant/main/static/backgroundimage.png");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }
        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.85);
            z-index: -1;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ====== 2. DEEPSEEK-STYLE CHAT UI ====== #
def main():
    st.set_page_config(
        page_title="EduBot Pro",
        page_icon="🎓",
        layout="wide"
    )
    set_background_image()

    # ---- Custom CSS for DeepSeek-like UI ---- #
    st.markdown("""
    <style>
    /* Fix input bar at bottom */
    .stChatInput {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 80%;
        max-width: 800px;
        background: white;
        border-radius: 25px;
        padding: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        z-index: 999;
    }
    /* Upload button styling */
    .st-emotion-cache-1hgxyac {
        margin-top: 10px !important;
        margin-left: 10px !important;
    }
    /* Message bubbles */
    .stChatMessage {
        max-width: 80%;
        margin: 0 auto;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---- Main Chat Interface ---- #
    st.title("🎓 EduBot Pro")
    st.caption("Your AI Education Consultant")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your education consultant. Ask me about universities or scholarships."}
        ]

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ---- DEEPSEEK-STYLE INPUT SECTION ---- #
    col1, col2 = st.columns([6, 1])
    with col1:
        user_input = st.chat_input("Ask about universities...", key="input")
    with col2:
        uploaded_file = st.file_uploader(
            "📎", 
            type=["pdf", "png", "jpg"],
            help="Upload documents",
            label_visibility="collapsed"
        )

    # ---- Handle User Input ---- #
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Simulate AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = f"Sample response to: {user_input}"
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    # ---- Handle File Upload ---- #
    if uploaded_file:
        st.session_state.messages.append({"role": "user", "content": f"📄 Uploaded: {uploaded_file.name}"})
        with st.chat_message("user"):
            st.markdown(f"📄 Uploaded: {uploaded_file.name}")
        
        # Process file (replace with your logic)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing document..."):
                st.markdown(f"✅ Successfully analyzed **{uploaded_file.name}**")

if __name__ == "__main__":
    main()
