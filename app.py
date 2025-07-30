import streamlit as st
from backend import EducationAgent
import json

# Initialize the AI agent
if "agent" not in st.session_state:
    st.session_state.agent = EducationAgent()
    st.session_state.chat_history = []

# Custom CSS to match your design
st.markdown("""
<style>
    .profile-section {
        border-bottom: 1px solid #eee;
        padding-bottom: 1rem;
        margin-bottom: 1rem;
    }
    .gpa-display {
        font-size: 1.1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Main layout
st.title("🎓 AI Education Consultant")
st.caption("Powered by GPT-4-turbo + Autonomous Agent")

# Sidebar for profile - matches your screenshot layout
with st.sidebar:
    st.header("Student Profile")
    
    # Degree section
    with st.container():
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        degree = st.selectbox("Degree", ["Bachelor's", "Master's", "PhD"])
        field_of_study = st.text_input("Field of Study")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Target country section
    with st.container():
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        country = st.text_input("Target Country")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # GPA section - single value display
    with st.container():
        st.markdown('<div class="profile-section">', unsafe_allow_html=True)
        st.markdown("**GPA (Scale 4.0)**")
        gpa = st.slider("", 0.0, 4.0, 3.5, 0.1, label_visibility="collapsed")
        st.markdown(f'<div class="gpa-display">{gpa}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Budget section
    with st.container():
        budget = st.number_input("Budget (USD/year)", min_value=1000, value=20000, step=1000)
    
    # Search button
    if st.button("Suggest Universities", type="primary"):
        st.session_state.agent.user_profile = {
            "degree": degree,
            "field_of_study": field_of_study,
            "country": country,
            "gpa": gpa,
            "budget": budget
        }
        
        # Show loading state
        with st.spinner("🔍 Searching for universities..."):
            # Get search steps
            task = f"Find {degree} programs in {country} for {field_of_study} with GPA {gpa} and budget {budget}"
            steps = st.session_state.agent._orchestrate_task(task)
            
            # Execute search if steps are available
            if steps and steps[0]["tool"] == "google_search":
                search_results = st.session_state.agent._use_tool(
                    "google_search", 
                    {"query": steps[0]["query"]}
                )
                
                if search_results:
                    formatted_results = st.session_state.agent._format_results(search_results)
                    st.session_state.chat_history.append(("AI", f"Found {len(search_results)} universities:"))
                    st.session_state.chat_history.append(("AI", formatted_results))
                else:
                    st.session_state.chat_history.append(("AI", "No universities found matching your criteria."))
            else:
                st.session_state.chat_history.append(("AI", "Could not perform search. Please check your profile details."))
        
        st.rerun()

# Main chat area
for role, message in st.session_state.chat_history:
    with st.chat_message(role):
        st.write(message)

# User input at bottom
if prompt := st.chat_input("Ask the AI consultant..."):
    st.session_state.chat_history.append(("User", prompt))
    response = st.session_state.agent.process_input(prompt)
    st.session_state.chat_history.append(("AI", response))
    st.rerun()
