import streamlit as st
import requests
import os
import re

# Configure page metadata and layout
st.set_page_config(page_title="RAG Document Q&A", layout="wide")

# Custom CSS to reduce top spacing
st.markdown("""
    <style>
        /* 1. Hide the hidden top bar to shift everything up */
        [data-testid="stHeader"] {
            display: none !important;
        }
        
        /* 2. Unified top padding for Sidebar and Main Area */
        [data-testid="stSidebarContent"], 
        [data-testid="stSidebarContent"] > div:first-child,
        [data-testid="stSidebarUserContent"],
        [data-testid="stSidebar"] section,
        [data-testid="stSidebarNav"] {
            padding-top: 1rem !important;
            margin-top: 0rem !important;
        }
        .main .block-container {
            padding-top: 1rem !important;
        }
        
        
        /* 4. Remove default margins from headers to ensure strict alignment */
        h1, h2, h3 {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        /* 6. Dimmed text utility */
        .dimmed-text {
            color: rgba(255, 255, 255, 0.6) !important;
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)

# API endpoint configuration
API_URL = os.getenv("API_URL", "http://rag-api-service:80")

# Define user_role early (needed for header)
user_role = "Admin"  # Default, will be overridden by sidebar

# Sidebar: Settings (Define user_role here)
with st.sidebar:
    st.header("Settings")
    user_role = st.selectbox(
        "Your Role",
        ["admin", "employee", "intern"],
        format_func=lambda x: x.title(),
        help="Determines access permissions"
    )
    st.divider()

# Header Layout
st.markdown("## RAG Document Q&A System")

# Helper functions for dynamic data
@st.cache_data(ttl=3600)
def fetch_domains():
    """Fetch available domains from API"""
    try:
        resp = requests.get(f"{API_URL}/domains", timeout=2)
        if resp.status_code == 200:
            return resp.json().get("domains", [])
    except:
        pass
    return ["general", "legal", "hr", "engineering"] # Fallback

def format_domain(d):
    if d is None:
        return "General"
    mapping = {"hr": "HR"} # Special cases
    return mapping.get(d, d.title())
def style_citations(text: str) -> str:
    """Wrap numeric citations like [1] in Streamlit blue color tags."""
    if not text:
        return text
    # Matches patterns like [1], [2], etc. and wraps them in :blue[[1]]
    return re.sub(r'(\[\d+\])', r':blue[\1]', text)



available_domains = fetch_domains()
domain = st.selectbox(
    "Select Domain",
    options=available_domains,
    format_func=format_domain,
    help="Filter documents by domain"
)

# Sidebar: Upload Documents (user_role already defined above)
with st.sidebar:
    st.header("Upload Documents")
    with st.expander("Upload a new document", expanded=True):
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'txt', 'docx'],
            help="Upload PDF, TXT, or DOCX files"
        )
        
        if uploaded_file and st.button("Upload"):
            st.toast(f"⏳ Uploading {uploaded_file.name}...")
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
                    st.success(f"{uploaded_file.name} uploaded successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Upload failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.markdown("---")
    st.markdown("""
    <div class="dimmed-text">
        <h3>🛠️ Tech Stack</h3>
        <ul>
            <li><strong>LLM</strong>: Amazon Nova (Bedrock)</li>
            <li><strong>Vector DB</strong>: ChromaDB</li>
            <li><strong>Backend</strong>: FastAPI</li>
            <li><strong>Frontend</strong>: Streamlit</li>
            <li><strong>Cache</strong>: Redis</li>
            <li><strong>Observability</strong>: Grafana + Prometheus</li>
            <li><strong>Infra</strong>: AWS EKS + Terraform</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Section for uploading new documents to the RAG knowledge base


# Interface for asking questions and retrieving answers

# Initialize session state variables
if "response" not in st.session_state:
    st.session_state.response = None

# Callback functions
def run_search():
    if st.session_state.question_input.strip():
        st.toast("🔍 Searching knowledge base...")
        try:
            api_response = requests.post(
                f"{API_URL}/query",
                json={"question": st.session_state.question_input, "domain": domain},
                headers={"x-user-role": user_role}
            )
            
            if api_response.status_code == 200:
                st.session_state.response = api_response.json()
            elif api_response.status_code == 403:
                st.session_state.response = {"error": "Access Denied: You don't have permission to access this domain"}
            else:
                st.session_state.response = {"error": f"Query failed: {api_response.text}"}
        except Exception as e:
            st.session_state.response = {"error": f"Error: {str(e)}"}
    else:
         st.warning("Please enter a question")

def clear_input():
    st.session_state.question_input = ""
    st.session_state.response = None

# Input section (Enter key triggers run_search)
st.text_input(
    "Enter your question",
    placeholder="e.g., What is the deployment process?",
    key="question_input",
    on_change=run_search
)

# Buttons layout (closer together)
# Buttons layout (closer together)
col1, col2, col3 = st.columns([1, 1.5, 12.5])
with col1:
    st.button("Search", type="primary", on_click=run_search)
with col2:
    st.button("Clear Text", on_click=clear_input)

# Display Answer logic
if st.session_state.response:
    result = st.session_state.response
    
    if "error" in result:
        st.error(result["error"])
    else:
        # Apply blue styling to numeric citations
        styled_answer = style_citations(result['answer'])
        st.write(styled_answer)
        
        col1, col2 = st.columns(2)
        with col1:
            raw_domain = result.get('domain') or 'general'
            display_domain = format_domain(raw_domain)
            st.metric("Domain", display_domain)
        with col2:
            exec_time_sec = result.get('execution_time_ms', 0) / 1000
            st.metric("Response Time", f"{exec_time_sec:.2f}s")
        
        with st.expander("Sources"):
            for idx, source in enumerate(result.get('sources', [])):
                st.write(f"**Source {idx+1}:**")
                st.json(source)