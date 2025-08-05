import streamlit as st
from backend import EducationAgent

import streamlit as st

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

    
# Set up the app
st.set_page_config(page_title="EduBot", page_icon="🎓")

# Initialize the agent
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm your education consultant. Tell me about your academic goals."}
    ]

# Title and description
st.title("🎓 EduBot - AI Education Consultant")
st.caption("A ChatGPT-like interface for university guidance")

# --- Sidebar Tools ---
with st.sidebar:
    st.header("📁 Document Tools")
    uploaded_file = st.file_uploader("Upload CV/Transcript", type=["pdf", "png", "jpg"])
    
    if uploaded_file:
        with st.spinner("Analyzing document..."):
            feedback = st.session_state.agent.analyze_document(
                uploaded_file.getvalue(),
                uploaded_file.type
            )
        st.success("✅ Analysis Complete")
        st.markdown(f"### Feedback:\n{feedback}")

# --- Display previous chat messages ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat input handler ---
if prompt := st.chat_input("Ask me about universities, scholarships, or paste a link..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if "http" in prompt:
                response = st.session_state.agent.analyze_scholarship_url(prompt)
            else:
                response = st.session_state.agent.chat(prompt)
        st.markdown(response)

        # Optional scholarship footer
        if "scholarship" in prompt.lower():
            st.markdown(
                """
                <div style="margin-top: 1rem; font-size: 0.85rem; color: gray;">
                📌 <em>Scholarship summaries are sourced via public RSS feeds from ScholarshipsCorner and ScholarshipUnion. For complete details, always refer to the original websites.</em>
                </div>
                """, unsafe_allow_html=True
            )

    # Save assistant message
    st.session_state.messages.append({"role": "assistant", "content": response})

# --- Tailored Application Button ---
if st.session_state.get("last_scholarship"):
    st.button("🤖 Get help tailoring your application", 
              on_click=lambda: st.session_state.messages.append(
                  {"role": "user", "content": "Help me apply to the last scholarship"}
              ))


