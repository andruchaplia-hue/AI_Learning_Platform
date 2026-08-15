import html
import httpx
import streamlit as st

from frontend.components.common_widgets import apply_custom_theme, render_platform_sidebar
from frontend.services.api_client import APIClient

st.set_page_config(
    page_title="UC1: Text Autocomplete | AI Learning Platform",
    page_icon="✨",
    layout="centered",
)

apply_custom_theme()
api_client = APIClient()
render_platform_sidebar(api_client, active_module="Autocomplete")

# Header section
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 class="main-title">✨ Use Case 1: AI Text Autocomplete</h1>
        <p class="sub-title">Powered by LangChain LCEL Architecture & Google Gemini Provider Gateway</p>
    </div>
    """,
    unsafe_allow_html=True,
)

default_text = st.session_state.get("input_text", "")

st.markdown("### 📝 Enter Your Text Prompt")
user_input = st.text_area(
    label="Text prompt",
    value=default_text,
    placeholder="Type the beginning of a sentence or paragraph here...",
    height=140,
    label_visibility="collapsed",
    key="text_input_area",
)

char_count = len(user_input.strip())
col_count, col_btn1, col_btn2 = st.columns([2, 1, 1])

with col_count:
    if char_count > 0:
        if char_count < 5:
            st.caption(f"⚠️ Character count: {char_count} (minimum 5 required)")
        elif char_count > 5000:
            st.caption(f"❌ Character count: {char_count} / 5000 (exceeds limit)")
        else:
            st.caption(f"✅ Character count: {char_count} / 5000")
    else:
        st.caption("Minimum required length: 5 characters.")

with col_btn1:
    btn_phrase = st.button(
        "✍️ Complete Sentence",
        type="secondary",
        width="stretch",
        disabled=(char_count < 5 or char_count > 5000),
    )

with col_btn2:
    btn_paragraph = st.button(
        "📖 Complete Paragraph",
        type="primary",
        width="stretch",
        disabled=(char_count < 5 or char_count > 5000),
    )

generate_clicked = btn_phrase or btn_paragraph
mode = "paragraph" if btn_paragraph else "sentence"

if generate_clicked:
    with st.spinner("✨ Generating autocomplete completion via LangChain..."):
        try:
            res = api_client.post_autocomplete(text=user_input, mode=mode)
            status_code = res["status_code"]
            data = res["data"]
            raw_resp = res["raw_response"]

            if status_code == 200 and data:
                exec_time = data.get("execution_time_sec", 0.0)
                completions = data.get("completions", [])
                if not completions and "completion" in data:
                    completions = [data["completion"]]

                st.markdown("### 📖 Completed Output")
                for idx, opt in enumerate(completions):
                    full_text = f"{user_input.strip()} {opt}"
                    with st.container(border=True):
                        if len(completions) > 1:
                            st.caption(f"**Option {idx + 1}**")

                        st.markdown(
                            f"<p style='font-size: 1.15rem; line-height: 1.7; margin-bottom: 0.5rem;'>"
                            f"<span style='color: #9CA3AF;'>{html.escape(user_input.strip())}</span> "
                            f"<span style='color: #60A5FA; font-weight: 600;'>{html.escape(opt)}</span>"
                            f"</p>",
                            unsafe_allow_html=True,
                        )
                        col_meta, col_copy = st.columns([3, 1])
                        with col_meta:
                            st.caption(f"⚡ Generated in {exec_time}s")
                        with col_copy:
                            if st.button("📋 Copy", key=f"btn_copy_{idx}_{mode}"):
                                st.toast("📋 Text copied!")
                                st.session_state["copied_text"] = full_text
            else:
                try:
                    err_data = raw_resp.json()
                    err_msg = err_data.get("message", raw_resp.text)
                except Exception:
                    err_msg = raw_resp.text

                st.error(f"Backend Error ({status_code}): {err_msg}")

        except httpx.ConnectError:
            st.error(
                f"🔌 Backend service is currently offline. Unable to connect to `{api_client.base_url}`. "
                "Please ensure the FastAPI backend is running."
            )
        except httpx.TimeoutException:
            st.error("⏳ Request timed out while waiting for LLM completion response.")
        except Exception as exc:
            st.error(f"An unexpected error occurred: {exc}")
