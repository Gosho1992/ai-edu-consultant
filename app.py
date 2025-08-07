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
        type=["pdf", "txt", "docx", "jpg", "png", "jpeg"],
        accept_multiple_files=False
    )
    
    if uploaded_file is not None:  # Check if file was actually uploaded
        file_extension = os.path.splitext(uploaded_file.name)[1][1:].lower()
        valid_types = ["cv", "resume", "transcript", "sop", "motivation letter"]
        
        doc_type = st.selectbox(
            "Select document type",
            valid_types,
            index=3 if "sop" in uploaded_file.name.lower() else 
                 0 if "resume" in uploaded_file.name.lower() or "cv" in uploaded_file.name.lower() else
                 1 if "transcript" in uploaded_file.name.lower() else 3
        )
        
        if st.button("Analyze Document"):
            with st.spinner(f"Analyzing your {doc_type}..."):
                try:
                    # Read file content directly
                    file_bytes = uploaded_file.read()
                    
                    # Normalize document type for backend
                    backend_doc_type = "cv" if doc_type in ["resume", "cv"] else doc_type
                    
                    # Ensure file is not empty
                    if len(file_bytes) == 0:
                        st.error("Uploaded file is empty")
                        st.stop()
                    
                    # Call backend analysis
                    analysis = st.session_state.agent.analyze_document(
                        file_bytes=file_bytes,
                        filename=uploaded_file.name,
                        doc_type=backend_doc_type
                    )
                    
                    # Check if analysis failed
                    if not analysis or analysis.get("error"):
                        error_msg = analysis.get("error", "Unknown error occurred during analysis")
                        st.error(f"❌ {error_msg}")
                    else:
                        # Display successful results
                        st.subheader("Analysis Results")
                        
                        if analysis.get("text"):
                            st.text_area("Extracted Text", 
                                       value=analysis["text"], 
                                       height=200,
                                       key="extracted_text")
                        
                        if analysis.get("feedback"):
                            st.text_area("Feedback", 
                                        value=analysis["feedback"], 
                                        height=200,
                                        key="feedback")
                        
                        if backend_doc_type == "sop" and analysis.get("enhanced_version"):
                            st.text_area("Enhanced Version", 
                                        value=analysis["enhanced_version"], 
                                        height=300,
                                        key="enhanced_version")
                
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    st.error("Please ensure you've uploaded a valid document file and selected the correct document type.")


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

