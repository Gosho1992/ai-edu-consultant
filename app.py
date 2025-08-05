import streamlit as st
from backend import EducationAgent
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Set background video from GitHub ---
def set_video_background_from_github():
    video_url = "https://raw.githubusercontent.com/Gosho1992/ai-edu-consultant/main/static/backgroundvideo.mp4"
    video_html = f"""
    <style>
    #root > div:first-child {{
        position: relative;
    }}
    #root > div:first-child::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        background: rgba(255,255,255,0.7);
    }}
    #bgVideo {{
        position: fixed;
        right: 0;
        bottom: 0;
        min-width: 100%;
        min-height: 100%;
        z-index: -2;
        opacity: 0.3;
    }}
    </style>
    <video autoplay muted loop id="bgVideo">
        <source src="{video_url}" type="video/mp4">
    </video>
    """
    st.markdown(video_html, unsafe_allow_html=True)

# --- Google Sheets setup ---
def init_gsheets():
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("scholarship-bot.json", scope)
    client = gspread.authorize(creds)
    return client.open("EduBot_Users").sheet1

# --- Welcome screen ---
def show_welcome_screen():
    welcome_html = """
    <style>
    .welcome-container {
        background: white;
        border-radius: 20px;
        padding: 3rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        max-width: 600px;
        margin: 0 auto;
        text-align: center;
    }
    </style>
    <div class="welcome-container">
        <h1>🎓 Welcome to EduBot Pro</h1>
        <p>Your personal AI education consultant</p>
        <img src="https://i.imgur.com/JDyhW5n.png" width="200">
    </div>
    """
    st.markdown(welcome_html, unsafe_allow_html=True)
    
    with st.form("user_form"):
        username = st.text_input("Enter your name to continue")
        if st.form_submit_button("Start"):
            if username:
                sheet = init_gsheets()
                sheet.append_row([username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                st.session_state.username = username
                st.session_state.welcome_complete = True
                st.rerun()
            else:
                st.warning("Please enter your name")

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="EduBot", page_icon="🎓")
    set_video_background_from_github()

    if not st.session_state.get("welcome_complete"):
        show_welcome_screen()
        return

    # Initialize agent
    if "agent" not in st.session_state:
        st.session_state.agent = EducationAgent()
        st.session_state.messages = [
            {"role": "assistant", "content": "Hi! I'm your education consultant. Tell me about your academic goals."}
        ]

    # --- Title ---
    st.title("🎓 EduBot - AI Education Consultant")
    st.caption("A ChatGPT-like interface for university guidance")

    # --- Sidebar tools ---
    with st.sidebar:
        st.header("📁 Document Tools")
        uploaded_file = st.file_uploader("Upload CV/Transcript", type=["pdf", "png", "jpg", "jpeg"])
        if uploaded_file:
            with st.spinner("Analyzing document..."):
                feedback = st.session_state.agent.analyze_document(
                    uploaded_file.getvalue(),
                    uploaded_file.type
                )
            st.success("✅ Analysis Complete")
            st.markdown(f"### Feedback:\n{feedback}")

    # --- Chat history ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Chat input ---
    if prompt := st.chat_input("Ask me about universities, scholarships, or paste a link..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if "http" in prompt:
                    response = st.session_state.agent.analyze_scholarship_url(prompt)
                else:
                    response = st.session_state.agent.chat(prompt)
            st.markdown(response)

            if "scholarship" in prompt.lower():
                st.markdown("""
                <div style="margin-top: 1rem; font-size: 0.85rem; color: gray;">
                📌 <em>Scholarship summaries are sourced via public RSS feeds from ScholarshipsCorner and ScholarshipUnion. For complete details, always refer to the original websites.</em>
                </div>
                """, unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": response})

    # --- Smart Application Helper ---
    if st.session_state.get("last_scholarship"):
        st.button("🤖 Get help tailoring your application", 
                  on_click=lambda: st.session_state.messages.append(
                      {"role": "user", "content": "Help me apply to the last scholarship"}
                  ))

# Run
if __name__ == "__main__":
    main()
