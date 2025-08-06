import streamlit as st
from backend import EducationAgent

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

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about universities or scholarships..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.agent.chat(prompt)
        st.markdown(response)
        
        # 👇 Optional footer for scholarship answers
        if "scholarship" in prompt.lower():
            st.markdown(
                """
                <div style="margin-top: 1rem; font-size: 0.85rem; color: gray;">
                📌 <em>Scholarship summaries are sourced via public RSS feeds from ScholarshipsCorner and ScholarshipUnion. For complete details, always refer to the original websites.</em>
                </div>
                """, unsafe_allow_html=True
            )
    
    # Add AI response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})


