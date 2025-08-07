import streamlit as st
from backend import EducationAgent
import os
from datetime import datetime

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

# Document upload section in sidebar
with st.sidebar:
    st.header("📄 Document Analysis")
    uploaded_file = st.file_uploader(
        "Upload your documents for analysis",
        type=["pdf", "txt", "docx", "jpg", "png"],
        accept_multiple_files=False
    )
    
    if uploaded_file:
        file_extension = os.path.splitext(uploaded_file.name)[1][1:].lower()
        valid_types = ["cv", "resume", "transcript", "sop"]
        
        doc_type = st.selectbox(
            "Select document type",
            valid_types,
            index=0 if "resume" in uploaded_file.name.lower() else 2
        )
        
        if st.button("Analyze Document"):
            with st.spinner(f"Analyzing your {doc_type}..."):
                try:
                    # Use in-memory processing (no temp files)
                    file_bytes = uploaded_file.getvalue()
                    
                    # Normalize doc_type for backend
                    backend_doc_type = "cv" if doc_type == "resume" else doc_type
                    
                    analysis = st.session_state.agent.analyze_document(
                        file_bytes, 
                        uploaded_file.name, 
                        backend_doc_type
                    )
                    
                    # Display results
                    if analysis.get("error"):
                        st.error(analysis["error"])
                    else:
                        st.subheader("Analysis Results")
                        st.text_area("Extracted Text", analysis["text"], height=200)
                        st.text_area("Feedback", analysis["feedback"], height=200)
                        
                        if doc_type == "sop" and analysis["enhanced_version"]:
                            st.text_area("Enhanced Version", analysis["enhanced_version"], height=300)
                    
                except Exception as e:
                    st.error(f"Error analyzing document: {str(e)}")

# Chat input
if prompt := st.chat_input("Ask me about universities or scholarships..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response - CHANGED FROM chat() TO generate_response()
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.agent.generate_response(prompt)
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
                
            except Exception as e:
                st.error(f"Error generating response: {str(e)}")
                response = "Sorry, I encountered an error. Please try again."
        
    # Add AI response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
