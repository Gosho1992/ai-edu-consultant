import streamlit as st
from backend import EducationAgent
import json

# Initialize the AI agent
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.chat_history = []

# Custom CSS
st.markdown("""
<style>
    .input-section {
        padding: 1rem;
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .gpa-display {
        font-size: 1.1rem;
        font-weight: bold;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎓 AI Education Consultant")
st.caption("Powered by GPT-4-turbo + Autonomous Agent")

# Input form (previously in sidebar)
with st.form("profile_form"):
    st.subheader("Your Profile")

    degree = st.selectbox("Degree", ["Bachelor's", "Master's", "PhD"])
    field_of_study = st.text_input("Field of Study")
    country = st.text_input("Target Country")
    gpa = st.slider("GPA (Scale 4.0)", 0.0, 4.0, 3.5, 0.1)
    st.markdown(f'<div class="gpa-display">GPA: {gpa}</div>', unsafe_allow_html=True)
    budget = st.number_input("Budget (USD/year)", min_value=1000, value=20000, step=1000)

    submitted = st.form_submit_button("Suggest Universities")

if submitted:
    st.session_state.agent.user_profile = {
        "degree": degree,
        "field_of_study": field_of_study,
        "country": country,
        "gpa": gpa,
        "budget": budget
    }

    with st.spinner("🔍 Searching for universities..."):
        task = f"Find {degree} programs in {country} for {field_of_study} with GPA {gpa} and budget {budget}"
        steps = st.session_state.agent._orchestrate_task(task)

        if steps and steps[0]["tool"] == "google_search":
            search_results = st.session_state.agent._use_tool("google_search", {"query": steps[0]["query"]})
            if search_results:
                formatted_results = st.session_state.agent._format_results(search_results)
                st.session_state.chat_history.append(("AI", f"Found {len(search_results)} universities:"))
                st.session_state.chat_history.append(("AI", formatted_results))
            else:
                st.session_state.chat_history.append(("AI", "No universities found matching your criteria."))
        else:
            st.session_state.chat_history.append(("AI", "Could not perform search. Please check your profile details."))

    st.rerun()

# Display chat history
for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.write(message)

# Chat input
if prompt := st.chat_input("Ask the AI consultant..."):
    st.session_state.chat_history.append(("User", prompt))
    response = st.session_state.agent.process_input(prompt)
    st.session_state.chat_history.append(("AI", response))
    st.rerun()
