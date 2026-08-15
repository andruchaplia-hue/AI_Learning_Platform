import streamlit as st

from frontend.components.common_widgets import apply_custom_theme, render_platform_sidebar
from frontend.services.api_client import APIClient

st.set_page_config(
    page_title="UC3: Image Captioning | AI Learning Platform",
    page_icon="🖼️",
    layout="wide",
)

apply_custom_theme()
api_client = APIClient()
render_platform_sidebar(api_client, active_module="UC3")

st.markdown('<h1 class="main-title">🖼️ Use Case 3: Image Captioning</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Multimodal vision analysis & caption generation using LangChain Expression Language (LCEL) & Google Gemini</p>',
    unsafe_allow_html=True,
)

col_upload, col_result = st.columns([1, 1], gap="large")

with col_upload:
    st.markdown("### 📤 Upload Image")
    uploaded_file = st.file_uploader(
        "Select an image file (PNG, JPG, JPEG, WEBP, GIF):",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        help="Upload an image up to 50 MB. Large images will be automatically compressed and downscaled for processing efficiency.",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name
        mime_type = uploaded_file.type or "image/png"

        st.image(file_bytes, caption=f"Selected File: {file_name}", width="stretch")

        if st.button("✨ Generate Image Caption", type="primary", width="stretch"):
            with st.spinner("🔍 Analyzing image with LangChain & Gemini Vision..."):
                res = api_client.post_image_caption(
                    file_bytes=file_bytes,
                    filename=file_name,
                    mime_type=mime_type,
                )

            if res["status_code"] == 200 and res["data"]:
                st.session_state["uc3_result"] = res["data"]
            else:
                err_msg = res["data"].get("message") if res["data"] else "Failed to generate caption."
                st.error(f"❌ Error ({res['status_code']}): {err_msg}")

with col_result:
    st.markdown("### 📝 Analysis Results")

    result = st.session_state.get("uc3_result")
    if result:
        # Display resize notification if auto-downscaled
        if result.get("resized"):
            st.warning(
                f"⚠️ **For resource optimization, the image was automatically resized** "
                f"from **{result.get('original_resolution')}** to **{result.get('processed_resolution')}**."
            )

        st.markdown("#### 🎯 Short Caption")
        st.info(f"**\"{result.get('short_caption')}\"**")

        st.markdown("#### 📖 Detailed Scene & Objects Description")
        st.success(result.get("full_description"))

        if result.get("action_description"):
            st.markdown("#### 🎬 Action & Activity Analysis")
            st.warning(result.get("action_description"))


        # Metadata metrics box
        st.divider()
        st.markdown("##### ⏱️ Performance & Processing Metadata")
        st.json(
            {
                "Execution Time": f"{result.get('execution_time_sec')} seconds",
                "Original Resolution": result.get("original_resolution"),
                "Processed Resolution": result.get("processed_resolution"),
                "Auto Resized": result.get("resized"),
                "Stored Image ID": result.get("image_id"),
            }
        )
    else:
        st.info("👈 Upload an image on the left panel and click **Generate Image Caption** to see multimodal results.")

st.divider()
if st.button("⬅️ Return to Home"):
    st.switch_page("Home.py")

