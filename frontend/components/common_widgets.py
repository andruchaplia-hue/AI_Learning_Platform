import streamlit as st

from frontend.services.api_client import APIClient


def apply_custom_theme() -> None:
    """Apply global CSS styles for dark glassmorphism aesthetic."""
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60A5FA 0%, #A855F7 50%, #EC4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        .sub-title {
            color: #9CA3AF;
            font-size: 1.2rem;
            margin-bottom: 2rem;
        }
        header[data-testid="stHeader"], header {
            visibility: hidden;
            height: 0px;
        }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_platform_sidebar(api_client: APIClient, active_module: str = "Home") -> None:
    """Render unified platform sidebar with health status check."""
    with st.sidebar:
        st.header("⚙️ Platform Health")
        backend_status = "🔴 Offline"
        provider_info = "Unknown"
        app_name = "Unknown"

        try:
            health = api_client.get_health()
            if health.get("status") == "ok":
                backend_status = "🟢 Online"
                version = api_client.get_version()
                provider_info = version.get("provider", "google").upper()
                app_name = version.get("app_name", "ai-learning-platform")
        except Exception:
            backend_status = "🔴 Offline"

        st.markdown(f"**Backend API:** {backend_status}")
        st.markdown(f"**Endpoint:** `{api_client.base_url}`")
        st.markdown(f"**LLM Provider:** `{provider_info}`")
        st.markdown(f"**Application:** `{app_name}`")
        st.divider()

        if active_module != "Home":
            if st.button("⬅️ Return to Platform Home", width="stretch"):
                st.switch_page("Home.py")
        else:
            st.info("💡 Select a Use Case from the left sidebar menu to begin.")
