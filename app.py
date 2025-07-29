import streamlit as st
from your_backend import EducationAgent  # Import your existing backend class
import json

# Initialize the AI agent
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.chat_history = []

# Streamlit UI
st.title("🎓 AI Education Consultant")
st.caption("Powered by GPT-4-turbo + Autonomous Agent")

# Sidebar for profile inputs
with st.sidebar:
    st.header("Student Profile")
    degree = st.selectbox("Degree", ["Bachelor's", "Master's", "PhD", "MBA"])
    field_of_study = st.text_input("Field of Study")
    country = st.text_input("Target Country")
    gpa = st.slider("GPA (Scale 4.0)", 0.0, 4.0, 3.5)
    budget = st.number_input("Budget (USD/year)", min_value=1000, value=20000)

    # Auto-fill suggestions
    if st.button("Suggest Universities"):
        st.session_state.agent.user_profile = {
            "degree": degree,
            "field_of_study": field_of_study,
            "country": country,
            "gpa": gpa,
            "budget": budget
        }
        st.session_state.chat_history.append(("AI", "🔍 Searching for universities..."))
        results = st.session_state.agent._orchestrate_task(f"Find {degree} programs in {country}")
        st.session_state.chat_history.append(("AI", f"Found {len(results)} options:"))

# Chat interface
for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.write(message)

# User input
if prompt := st.chat_input("Ask the AI consultant..."):
    st.session_state.chat_history.append(("User", prompt))
    
    # Get AI response
    response = st.session_state.agent.process_input(prompt)  # Add this method to your backend
    st.session_state.chat_history.append(("AI", response))
    st.rerun()