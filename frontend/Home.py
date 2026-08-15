import streamlit as st

from frontend.components.common_widgets import apply_custom_theme, render_platform_sidebar
from frontend.services.api_client import APIClient

# Configure page metadata and layout
st.set_page_config(
    page_title="AI Learning Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_theme()
api_client = APIClient()
render_platform_sidebar(api_client, active_module="Home")

# Header Section
st.markdown('<h1 class="main-title">🎓 AI Learning Platform</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Unified Enterprise Platform for Generative AI & Agentic Use Cases</p>',
    unsafe_allow_html=True,
)

# Main Overview Grid
st.markdown("### 🚀 Available Learning Modules")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("### ✍️ Use Case 1: Text Autocomplete")
        st.markdown(
            "Fast intelligent text completion using LangChain LCEL pipeline & Google Gemini."
        )
        st.caption("Framework: **LangChain (LCEL)** | Status: 🟢 Ready")
        if st.button("Open Text Autocomplete ➡️", key="btn_uc1", type="primary"):
            st.switch_page("pages/01_Autocomplete.py")

    with st.container(border=True):
        st.markdown("### 🖼️ Use Case 3: Image Captioning")
        st.markdown("Multimodal image analysis and automatic prompt generation.")
        st.caption("Framework: **LangChain Vision** | Status: 🟢 Ready")
        if st.button("Open Image Captioning ➡️", key="btn_uc3", type="primary"):
            st.switch_page("pages/03_Image_Captioning.py")


    with st.container(border=True):
        st.markdown("### 🎯 Use Case 5: Content Generator")
        st.markdown(
            "Personalized content generation tailored to user profile preferences & history."
        )
        st.caption("Framework: **LangChain Agent + Auth** | Status: 🟢 Ready")
        if st.button("Open Content Generator ➡️", key="btn_uc5", type="primary"):
            st.switch_page("pages/05_Content_Generator.py")

with col2:
    with st.container(border=True):
        st.markdown("### 💬 Use Case 2: FAQ Assistant")
        st.markdown(
            "Conversational RAG assistant with vector search, query decomposition, and Semantic Kernel AI Agents."
        )
        st.caption("Framework: **Semantic Kernel Agents** | Status: 🟢 Ready")
        if st.button("Open FAQ Assistant ➡️", key="btn_uc2", type="primary"):
            st.switch_page("pages/02_FAQ_Assistant.py")


    with st.container(border=True):
        st.markdown("### 💻 Use Case 4: Code Generation Assistant")
        st.markdown("Automated code generation, multi-agent review, visual diff refactoring, and fine-tuning hub.")
        st.caption("Framework: **Semantic Kernel Agents** | Status: 🟢 Ready")
        if st.button("Open Code Generation ➡️", key="btn_uc4", type="primary"):
            st.switch_page("pages/04_Code_Generation.py")


st.divider()
st.markdown(
    "#### 🏛️ Architecture Highlights\n"
    "- **Clean Architecture**: Decoupled UI, REST API, Application Services, and Infrastructure Gateway.\n"
    "- **Multi-Framework Gateway**: Single LLM Gateway serving both **LangChain** and **Semantic Kernel**.\n"
    "- **Modular Use Cases**: Business logic encapsulated in `backend/use_cases/` modules."
)
