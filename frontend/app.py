import streamlit as st
import requests
import os

# Configure page metadata and layout
st.set_page_config(page_title="RAG Document Q&A", layout="wide")

""" Streamlit-based UI for interacting with the RAG API """

# API endpoint configuration
API_URL = os.getenv("API_URL", "http://rag-api-service:80")


st.title("🔍 RAG Document Q&A System")

# Sidebar configuration for domain and user role selection
with st.sidebar:
    st.header("Settings")
    domain = st.selectbox(
        "Select Domain",
        ["general", "legal", "hr", "engineering"],
        help="Filter documents by domain"
    )
    
    user_role = st.selectbox(
        "Your Role",
        ["admin", "employee", "intern"],
        help="Determines access permissions"
    )

# Section for uploading new documents to the RAG knowledge base
st.header("📤 Upload Documents")
with st.expander("Upload a new document"):
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'txt', 'docx'],
        help="Upload PDF, TXT, or DOCX files"
    )
    
    if uploaded_file and st.button("Upload"):
        with st.spinner("Uploading..."):
            files = {'file': uploaded_file}
            params = {'domain': domain}
            
            try:
                # Send file to the document ingestion endpoint
                response = requests.post(
                    f"{API_URL}/documents/upload",
                    files=files,
                    params=params
                )
                
                if response.status_code == 200:
                    st.success(f"✅ {uploaded_file.name} uploaded successfully!")
                    st.json(response.json())
                else:
                    st.error(f"❌ Upload failed: {response.text}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# Interface for asking questions and retrieving answers
st.header("💬 Ask Questions")
question = st.text_input(
    "Enter your question",
    placeholder="e.g., What is the deployment process?"
)

if st.button("Search", type="primary"):
    if not question:
        st.warning("Please enter a question")
    else:
        with st.spinner("Searching..."):
            try:
                # Query the RAG service with domain filtering and RBAC role
                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": question, "domain": domain},
                    headers={"x-user-role": user_role}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display the AI-generated answer
                    st.subheader("Answer")
                    st.write(result['answer'])
                    
                    # Display performance metrics and domain context
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Domain", result.get('domain', 'N/A'))
                    with col2:
                        st.metric("Response Time", f"{result.get('execution_time_ms', 0)}ms")
                    
                    # Expandable section for retrieved document chunks
                    with st.expander("📚 Sources"):
                        for idx, source in enumerate(result.get('sources', [])):
                            st.write(f"**Source {idx+1}:**")
                            st.json(source)
                
                # Handle unauthorized access cases
                elif response.status_code == 403:
                    st.error("🚫 Access Denied: You don't have permission to access this domain")
                else:
                    st.error(f"❌ Query failed: {response.text}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")