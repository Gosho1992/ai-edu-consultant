import streamlit as st
import requests
import base64

# --- Background ---
def set_background():
    css = f'''
    <style>
        [data-testid="stAppViewContainer"] > .main {{
            background-image: url("https://raw.githubusercontent.com/Gosho1992/ai-edu-consultant/main/static/backgroundimage.png");
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
            background-color: rgba(255, 255, 255, 0.85);
            z-index: 0;
        }}
        [data-testid="stAppViewContainer"] > .main > div {{
            position: relative;
            z-index: 1;
        }}
    </style>
    '''
    st.markdown(css, unsafe_allow_html=True)

# --- App Content ---
def main():
    st.set_page_config(page_title="EduBot Pro", page_icon="🎓", layout="wide")
    set_background()

    st.markdown("""
    <h1 style='font-size: 42px;'>🎓 EduBot Pro</h1>
    <p style='font-size: 18px;'>Your AI Education Consultant</p>
    <hr>
    """, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display previous messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Input bar ---
    user_prompt = st.chat_input("Ask about universities or scholarships…")

    # --- Upload section below input ---
    uploaded_file = st.file_uploader("Upload your CV, SOP, or Transcript", type=["pdf", "jpg", "png", "jpeg"], label_visibility="visible")

    if user_prompt or uploaded_file:
        # Display user message
        if user_prompt:
            st.chat_message("user").markdown(user_prompt)
            st.session_state.messages.append({"role": "user", "content": user_prompt})

        # Backend request
        with st.spinner("Thinking..."):
            response = requests.post(
                "https://your-backend-url.com/ask",
                headers={"X-API-KEY": st.secrets["API_KEY"]},
                json={"prompt": user_prompt} if not uploaded_file else None,
                files={"file": uploaded_file.getvalue()} if uploaded_file else None
            )

            if response.status_code == 200:
                bot_response = response.json().get("response")
            else:
                bot_response = "Sorry, something went wrong."

        st.chat_message("assistant").markdown(bot_response)
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

if __name__ == "__main__":
    main()
