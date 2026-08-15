import base64
import json
import streamlit as st

from frontend.services.api_client import APIClient

st.set_page_config(
    page_title="UC5: Personalized Content Studio | AI Learning Platform",
    page_icon="🎯",
    layout="wide",
)

client = APIClient()

# Initialize session state for authentication
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "last_generation" not in st.session_state:
    st.session_state.last_generation = None

st.title("🎯 Use Case 5: Personalized Content Studio")
st.caption(
    "Flagship Multi-Step Agent Framework (LangChain LCEL) + JWT Security + Personalization Vector RAG + Multimodal Vision"
)

# Top Status Bar
col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
with col_s1:
    try:
        health = client.get_health()
        st.success(f"Backend Status: {health.get('status', 'ok').upper()}")
    except Exception:
        st.error("Backend Disconnected")

with col_s2:
    try:
        ver = client.get_version()
        st.info(f"Provider: {ver.get('provider', 'google').upper()}")
    except Exception:
        st.info("Provider: DEFAULT")

with col_s3:
    if st.session_state.auth_token and st.session_state.user_info:
        u = st.session_state.user_info
        st.success(f"👤 Authenticated: **{u.get('username')}** ({u.get('email')})")
    else:
        st.warning("🔒 Authentication Required for Content Studio")

st.divider()

# -----------------------------------------------------------------------------
# 1. Unauthenticated View (Auth Guard Card)
# -----------------------------------------------------------------------------
if not st.session_state.auth_token:
    st.markdown("### 🔐 User Authentication & Security Gateway")
    st.info(
        "Use Case 5 utilizes JWT token-based authentication to securely isolate your personal profiles, "
        "writing tone rules, and style exemplars in ChromaDB."
    )

    auth_tab_dev, auth_tab1, auth_tab2 = st.tabs([
        "⚡ Quick Dev Login (Fast Auth)",
        "🔑 Standard Log In",
        "📝 Create Account",
    ])

    with auth_tab_dev:
        st.markdown("#### ⚡ One-Click Developer & Demo Login")
        st.caption("Select any registered user from the database or enter an email/username to log in instantly without typing a password.")

        dev_users_res = client.get_dev_users()
        dev_users = dev_users_res.get("data", []) if dev_users_res.get("status_code") == 200 else []

        if isinstance(dev_users, list) and len(dev_users) > 0:
            user_options = {
                f"👤 {u.get('username')} ({u.get('email')}) — {u.get('profession') or 'User'} [{u.get('writing_tone') or 'Standard'}]": u.get("email")
                for u in dev_users
            }
            selected_user_label = st.selectbox(
                "Select existing user from database:",
                options=list(user_options.keys()),
                key="dev_user_select",
            )
            selected_identifier = user_options[selected_user_label]

            col_dev_btn, _ = st.columns([2, 3])
            with col_dev_btn:
                if st.button("🚀 Fast Login as Selected User", type="primary", use_container_width=True):
                    with st.spinner(f"Logging in as {selected_identifier}..."):
                        res = client.dev_login(identifier=selected_identifier)
                        if res.get("status_code") == 200 and res.get("data"):
                            data = res["data"]
                            st.session_state.auth_token = data.get("access_token")
                            st.session_state.user_info = {
                                "id": data.get("user_id"),
                                "username": data.get("username"),
                                "email": data.get("email"),
                            }
                            st.success(f"Logged in as {data.get('username')}!")
                            st.rerun()
                        else:
                            err = res.get("data", {}).get("message", "Dev login failed.")
                            st.error(f"Login error: {err}")
        else:
            st.info("No registered users found in database yet. You can quick-login with any email or create an account.")

        st.divider()
        st.markdown("##### Or enter identifier directly:")
        col_inp, col_go = st.columns([3, 1])
        with col_inp:
            manual_dev_id = st.text_input("Username or Email", value="alex@example.com", key="manual_dev_id")
        with col_go:
            st.write("")
            st.write("")
            if st.button("⚡ Login", key="btn_manual_dev_login", use_container_width=True):
                with st.spinner(f"Logging in as {manual_dev_id}..."):
                    res = client.dev_login(identifier=manual_dev_id)
                    if res.get("status_code") == 200 and res.get("data"):
                        data = res["data"]
                        st.session_state.auth_token = data.get("access_token")
                        st.session_state.user_info = {
                            "id": data.get("user_id"),
                            "username": data.get("username"),
                            "email": data.get("email"),
                        }
                        st.success(f"Logged in as {data.get('username')}!")
                        st.rerun()
                    else:
                        err = res.get("data", {}).get("message", "User not found.")
                        st.error(f"Login error: {err}")

    with auth_tab1:
        with st.form("login_form"):
            st.markdown("#### Log In to Content Studio")
            login_email = st.text_input("Email Address", value="alex@example.com")
            login_password = st.text_input("Password", type="password", value="password123")
            login_submitted = st.form_submit_button("Log In 🚀", type="primary")

            if login_submitted:
                if not login_email or not login_password:
                    st.error("Please enter email and password.")
                else:
                    with st.spinner("Authenticating..."):
                        res = client.login(email=login_email, password=login_password)
                        if res.get("status_code") == 200 and res.get("data"):
                            data = res["data"]
                            st.session_state.auth_token = data.get("access_token")
                            st.session_state.user_info = {
                                "id": data.get("user_id"),
                                "username": data.get("username"),
                                "email": data.get("email"),
                            }
                            st.success(f"Welcome back, {data.get('username')}!")
                            st.rerun()
                        else:
                            err = res.get("data", {}).get("message", "Invalid email or password.")
                            st.error(f"Login failed: {err}")

    with auth_tab2:
        with st.form("register_form"):
            st.markdown("#### Register New Account")
            reg_username = st.text_input("Username", value="developer_pro")
            reg_email = st.text_input("Email Address", value="dev@example.com")
            reg_password = st.text_input("Password (min 6 characters)", type="password", value="secret123")
            reg_submitted = st.form_submit_button("Sign Up & Open Studio ✨", type="primary")

            if reg_submitted:
                if len(reg_username) < 3 or len(reg_password) < 6 or "@" not in reg_email:
                    st.error("Please ensure username >= 3 chars, password >= 6 chars, and valid email.")
                else:
                    with st.spinner("Creating account..."):
                        res = client.register(
                            username=reg_username, email=reg_email, password=reg_password
                        )
                        if res.get("status_code") in (200, 201) and res.get("data"):
                            data = res["data"]
                            st.session_state.auth_token = data.get("access_token")
                            st.session_state.user_info = {
                                "id": data.get("user_id"),
                                "username": data.get("username"),
                                "email": data.get("email"),
                            }
                            st.success("Account created successfully!")
                            st.rerun()
                        else:
                            err = res.get("data", {}).get("message", "Registration error.")
                            st.error(f"Registration failed: {err}")

    st.stop()

# -----------------------------------------------------------------------------
# 2. Authenticated View (Full 3-Tab Studio)
# -----------------------------------------------------------------------------

# Logout row
col_head, col_btn = st.columns([6, 1])
with col_head:
    st.markdown(f"### 🎨 Studio Workspace (`{st.session_state.user_info.get('username')}`)")
with col_btn:
    if st.button("🚪 Log Out", key="btn_logout", type="secondary"):
        st.session_state.auth_token = None
        st.session_state.user_info = None
        st.session_state.last_generation = None
        st.rerun()

tab_wall, tab_studio, tab_profile, tab_dataset = st.tabs([
    "📰 Profile Wall (Feed)",
    "✍️ Content Studio",
    "👤 Author Profile & Tone Calibration",
    "📚 Personalization Dataset (RAG & Fine-Tuning)",
])

# -----------------------------------------------------------------------------
# TAB 1: Profile Wall (Feed)
# -----------------------------------------------------------------------------
with tab_wall:
    col_w_head, col_w_btn = st.columns([5, 1])
    with col_w_head:
        st.markdown("#### 📰 Published Posts & Articles Feed")
        st.caption("All finalized posts submitted through the Content Studio appear on your public wall.")
    with col_w_btn:
        if st.button("🔄 Refresh", key="btn_refresh_wall"):
            st.rerun()

    hist_res = client.get_content_history(token=st.session_state.auth_token)
    posts = hist_res.get("data", []) if hist_res.get("status_code") == 200 and isinstance(hist_res.get("data"), list) else []

    if not posts:
        st.info("No posts published to your wall yet. Generate and submit content in the **✍️ Content Studio** to publish your first post!")
    else:
        for idx, post in enumerate(posts):
            p_type = post.get("content_type", "post")
            p_date = post.get("created_at", "")[:10]
            p_rating = post.get("rating", 0)
            p_img_path = post.get("image_path", "")
            p_content = post.get("generated_content", "")
            p_prompt = post.get("prompt", "")

            stars_str = f" ⭐ ({p_rating}/5)" if p_rating > 0 else ""

            # Card Header Badge by Content Type
            if p_type == "marketing_email":
                with st.container(border=True):
                    st.markdown(
                        f"""
<div translate="no" class="notranslate" style="background: #2b313e; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid #f59e0b;">
    <span style="font-weight: bold; color: #fbbf24;">✉️ MARKETING EMAIL CAMPAIGN</span>
    <span style="float: right; font-size: 0.85em; color: #94a3b8;">📅 {p_date}{stars_str}</span>
    <div style="font-size: 0.85em; color: #cbd5e1; margin-top: 4px;"><strong>Target Prompt:</strong> {p_prompt}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )
                    if p_img_path:
                        img_bytes = client.get_image_bytes(p_img_path)
                        if img_bytes:
                            st.image(img_bytes, caption="Campaign Visual Asset", width=360)
                    st.markdown(p_content)

            elif p_type == "linkedin_post":
                with st.container(border=True):
                    st.markdown(
                        f"""
<div translate="no" class="notranslate" style="background: #1e293b; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid #0ea5e9;">
    <span style="font-weight: bold; color: #38bdf8;">💼 LINKEDIN PROFESSIONAL POST</span>
    <span style="float: right; font-size: 0.85em; color: #94a3b8;">📅 {p_date}{stars_str}</span>
    <div style="font-size: 0.85em; color: #cbd5e1; margin-top: 4px;"><strong>Topic:</strong> {p_prompt}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )
                    if p_img_path:
                        img_bytes = client.get_image_bytes(p_img_path)
                        if img_bytes:
                            st.image(img_bytes, caption="Post Visual Media", width=360)
                    st.markdown(p_content)

            elif p_type == "blog_post":
                with st.container(border=True):
                    st.markdown(
                        f"""
<div translate="no" class="notranslate" style="background: #1e1e2e; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid #8b5cf6;">
    <span style="font-weight: bold; color: #a78bfa;">📝 LONG-FORM BLOG POST & ARTICLE</span>
    <span style="float: right; font-size: 0.85em; color: #94a3b8;">📅 {p_date}{stars_str}</span>
    <div style="font-size: 0.85em; color: #cbd5e1; margin-top: 4px;"><strong>Article Focus:</strong> {p_prompt}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )
                    if p_img_path:
                        img_bytes = client.get_image_bytes(p_img_path)
                        if img_bytes:
                            st.image(img_bytes, caption="Featured Article Header", width=420)
                    st.markdown(p_content)

            else:
                with st.container(border=True):
                    st.markdown(
                        f"""
<div translate="no" class="notranslate" style="background: #1e293b; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid #10b981;">
    <span style="font-weight: bold; color: #34d399;">💬 SOCIAL MEDIA POST (CASUAL)</span>
    <span style="float: right; font-size: 0.85em; color: #94a3b8;">📅 {p_date}{stars_str}</span>
    <div style="font-size: 0.85em; color: #cbd5e1; margin-top: 4px;"><strong>Prompt:</strong> {p_prompt}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )
                    if p_img_path:
                        img_bytes = client.get_image_bytes(p_img_path)
                        if img_bytes:
                            st.image(img_bytes, caption="Attached Snap", width=300)
                    st.markdown(p_content)

            st.write("")
with tab_profile:
    st.markdown("#### 👤 Author Profile & Tone Calibration")
    st.caption("Personal attributes configured here directly guide the Agent's grammatical gender, vocabulary, worldview, and facts.")

    prof_res = client.get_profile(token=st.session_state.auth_token)
    profile_data = prof_res.get("data", {}) if prof_res.get("status_code") == 200 else {}

    with st.form("profile_form"):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            p_profession = st.text_input("Profession / Role", value=profile_data.get("profession", "Senior Software Engineer"))
            p_industry = st.text_input("Industry / Domain", value=profile_data.get("industry", "Fintech / Cloud Architecture"))
            p_age = st.number_input("Age (Возраст)", min_value=14, max_value=120, value=int(profile_data.get("age") or 30), step=1)
            lang_opts = ["English", "Russian", "German", "Spanish"]
            lang_idx = lang_opts.index(profile_data.get("preferred_language")) if profile_data.get("preferred_language") in lang_opts else 0
            p_lang = st.selectbox("Preferred Language", lang_opts, index=lang_idx)

        with col_p2:
            cur_gender = profile_data.get("gender", "Male")
            gender_opts = ["Male", "Female"]
            gender_idx = 1 if cur_gender == "Female" else 0
            p_gender = st.selectbox("Gender (Пол — для грамматики от 1-го лица)", gender_opts, index=gender_idx)

            hobbies_raw = profile_data.get("hobbies") or profile_data.get("interests", ["AI", "Clean Architecture", "Coffee"])
            p_hobbies = st.text_input(
                "Hobbies & Passions (Хобби через запятую)",
                value=", ".join(hobbies_raw) if isinstance(hobbies_raw, list) else str(hobbies_raw),
                help="Analogies and worldview context will be drawn from your hobbies.",
            )

        p_bio = st.text_area(
            "About Me & Background Facts (О себе, факты и стиль):",
            height=120,
            value=profile_data.get(
                "bio",
                profile_data.get(
                    "style_notes",
                    "Software engineer with a passion for clean architecture and practical ML. Clear structure, dry humor, zero corporate buzzwords.",
                ),
            ),
            help="Include key facts, career milestones, or style preferences you want the agent to ground posts in.",
        )

        save_profile_btn = st.form_submit_button("💾 Save Profile Settings", type="primary")

        if save_profile_btn:
            hobbies_list = [i.strip() for i in p_hobbies.split(",") if i.strip()]
            payload = {
                "profession": p_profession,
                "industry": p_industry,
                "age": int(p_age),
                "gender": p_gender,
                "preferred_language": p_lang,
                "hobbies": hobbies_list,
                "bio": p_bio,
            }
            update_res = client.update_profile(profile_data=payload, token=st.session_state.auth_token)
            if update_res.get("status_code") == 200:
                st.success("Profile updated successfully! New generations will reflect your updated persona and facts.")
            else:
                st.error("Failed to update profile.")

# -----------------------------------------------------------------------------
# TAB 2: Content Studio
# -----------------------------------------------------------------------------
with tab_studio:
    st.markdown("#### 🚀 Multi-Step Personalized Content Generator")
    st.caption("Orchestrates Planner → Few-Shot RAG → Vision Extractor (Optional) → Editorial Stylist")

    col_input, col_preview = st.columns([1, 1], gap="medium")

    with col_input:
        content_type_label = st.radio(
            "Target Content Format:",
            options=["Blog Post", "LinkedIn Post", "Marketing Email", "Social Media Post (Short & Casual)"],
            horizontal=True,
        )
        type_mapping = {
            "Blog Post": "blog_post",
            "LinkedIn Post": "linkedin_post",
            "Marketing Email": "marketing_email",
            "Social Media Post (Short & Casual)": "social_media_post",
        }
        selected_type = type_mapping[content_type_label]

        prompt_input = st.text_area(
            "Content Topic & Instructions:",
            height=140,
            placeholder="e.g. Announce our newly designed AI Learning Platform built on Clean Architecture, supporting LangChain LCEL, Semantic Kernel multi-agent workflows, and ChromaDB vector search.",
            help="Describe what you want to write about. The agent will adapt it to your profile and style.",
            key="uc5_prompt_input_field",
        )

        use_personalization = st.checkbox(
            "🧠 Retrieve Style Exemplars from Personal ChromaDB Dataset (Few-Shot RAG)",
            value=True,
        )

        st.markdown("##### 🖼️ Optional Multimodal Visual Context")
        uploaded_image = st.file_uploader(
            "Upload Image/Diagram (Optional)",
            type=["png", "jpg", "jpeg", "webp"],
            help="Gemini Vision will extract narrative details to embed in the article or post.",
        )

        image_b64 = None
        image_mime = None
        raw_uploaded_bytes = None
        if uploaded_image is not None:
            raw_uploaded_bytes = uploaded_image.read()
            image_b64 = base64.b64encode(raw_uploaded_bytes).decode("utf-8")
            image_mime = uploaded_image.type or "image/jpeg"
            st.image(raw_uploaded_bytes, caption="Visual Reference Preview", width=260)

        generate_btn = st.button("✨ Generate Personalized Content", type="primary", use_container_width=True)

        if generate_btn:
            if not prompt_input or len(prompt_input.strip()) < 5:
                st.error("Please enter a prompt of at least 5 characters.")
            else:
                with st.spinner("⚡ Running Multi-Step Agent Pipeline (Planner → Personalization RAG → Generator)..."):
                    res = client.post_content_generation(
                        content_type=selected_type,
                        prompt=prompt_input,
                        token=st.session_state.auth_token,
                        image_base64=image_b64,
                        image_mime_type=image_mime,
                        use_personalization_dataset=use_personalization,
                    )

                    if res.get("status_code") == 200 and res.get("data"):
                        st.session_state.last_generation = res["data"]
                        st.success(f"Generated successfully in {res['data'].get('execution_time', 0)}s!")
                    else:
                        err = res.get("data", {}).get("message", "Generation error occurred.")
                        st.error(f"Generation failed: {err}")

    with col_preview:
        gen_data = st.session_state.last_generation
        if gen_data:
            st.markdown(f"### 🎴 Generated {content_type_label} Preview")

            # Metrics badges at top of preview
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Execution Time", f"{gen_data.get('execution_time', 0)}s")
            with m2:
                st.metric("Few-Shot Exemplars", f"{gen_data.get('few_shot_examples_count', 0)}")
            with m3:
                vis_status = "Yes (Gemini Vision)" if gen_data.get("visual_context_used") else "No"
                st.metric("Vision Context", vis_status)

            # Styled Post Card matching Wall design
            c_type = gen_data.get("content_type", selected_type)
            c_date = gen_data.get("created_at", "")[:10]
            c_prompt = gen_data.get("prompt", prompt_input)
            c_content = gen_data.get("generated_content", "")
            c_img_path = gen_data.get("image_path", "")

            badge_config = {
                "marketing_email": ("✉️ MARKETING EMAIL CAMPAIGN", "#2b313e", "#fbbf24", "#f59e0b", 360),
                "linkedin_post": ("💼 LINKEDIN PROFESSIONAL POST", "#1e293b", "#38bdf8", "#0ea5e9", 360),
                "blog_post": ("📝 LONG-FORM BLOG POST & ARTICLE", "#1e1e2e", "#a78bfa", "#8b5cf6", 420),
                "social_media_post": ("💬 SOCIAL MEDIA POST (CASUAL)", "#1e293b", "#34d399", "#10b981", 300),
            }
            badge_title, bg_color, text_color, border_color, img_w = badge_config.get(
                c_type, ("📰 POST", "#1e293b", "#38bdf8", "#0ea5e9", 360)
            )

            # 1. Agent Decision Chain Expander (Rendered ABOVE the generated post)
            if gen_data.get("decision_chain"):
                with st.expander("🧠 View Agent Thought Process & Decision Chain", expanded=False):
                    for step in gen_data["decision_chain"]:
                        st.markdown(f"**{step.get('stage')}**")
                        details_text = step.get("details", "")
                        if "\n" in details_text:
                            st.markdown(details_text)
                        else:
                            st.caption(details_text)
                        if step.get("samples"):
                            for s in step["samples"]:
                                tags_str = f" (Tags: {', '.join(s.get('tags', []))})" if s.get('tags') else ""
                                st.markdown(f"- 📄 `{s.get('title')}`{tags_str}")
                        st.divider()

            # 2. Generated Post Card
            gen_id = gen_data.get("id")
            feedback_state_key = f"feedback_saved_{gen_id}"
            is_submitted = bool(st.session_state.get(feedback_state_key))

            with st.container(border=True):
                st.markdown(
                    f"""
<div translate="no" class="notranslate" style="background: {bg_color}; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; border-left: 4px solid {border_color};">
    <span style="font-weight: bold; color: {text_color};">{badge_title}</span>
    <span style="float: right; font-size: 0.85em; color: #94a3b8;">📅 {c_date}</span>
    <div style="font-size: 0.85em; color: #cbd5e1; margin-top: 4px;"><strong>Topic:</strong> {c_prompt}</div>
</div>
""",
                    unsafe_allow_html=True,
                )
                if c_img_path:
                    card_img_bytes = client.get_image_bytes(c_img_path)
                    if card_img_bytes:
                        st.image(card_img_bytes, caption="Attached Visual Media", width=img_w)
                    elif raw_uploaded_bytes:
                        st.image(raw_uploaded_bytes, caption="Attached Visual Media", width=img_w)

                if not is_submitted:
                    edited_draft = st.text_area(
                        "✏️ Review & Edit Draft (editable before submitting to Wall):",
                        value=c_content,
                        height=200,
                        key=f"edit_draft_{gen_id}",
                        help="Feel free to tweak phrases, adjust length, or personalize the text before publishing.",
                    )
                else:
                    saved_info = st.session_state[feedback_state_key]
                    final_saved_text = saved_info.get("final_content", c_content)
                    st.markdown(final_saved_text)

            st.divider()

            # 3. Feedback & Rating Loop
            st.markdown("##### 🚀 Publish to Profile Wall & Rate")

            if is_submitted:
                saved_info = st.session_state[feedback_state_key]
                st.success(
                    f"✅ Post submitted and published to your Profile Wall ({saved_info.get('rating', 5)} ⭐). "
                    f"{'Sample saved to personal writing dataset.' if saved_info.get('saved_to_dataset') else ''}"
                )
            else:
                col_rate, col_save, col_sub = st.columns([1, 2, 1])
                with col_rate:
                    rating = st.selectbox("Rating:", [5, 4, 3, 2, 1], index=0, key=f"rating_box_{gen_id}")
                with col_save:
                    save_to_dataset = st.checkbox(
                        "Save to personal writing dataset (Few-Shot RAG)",
                        value=(rating >= 4),
                        key=f"save_chk_{gen_id}",
                    )
                with col_sub:
                    st.write("")
                    if st.button("🚀 Submit Post", key=f"btn_feedback_{gen_id}", type="primary", use_container_width=True):
                        content_to_submit = edited_draft.strip() if 'edited_draft' in locals() and edited_draft.strip() else c_content
                        feed_res = client.submit_content_post(
                            prompt=gen_data.get("prompt", prompt_input),
                            content_type=gen_data.get("content_type", selected_type),
                            generated_content=content_to_submit,
                            plan_breakdown=gen_data.get("plan_breakdown", ""),
                            image_path=gen_data.get("image_path", ""),
                            rating=rating,
                            save_to_dataset=save_to_dataset,
                            token=st.session_state.auth_token,
                        )
                        if feed_res.get("status_code") in (200, 201):
                            st.session_state[feedback_state_key] = {
                                "rating": rating,
                                "saved_to_dataset": save_to_dataset,
                                "final_content": content_to_submit,
                            }
                            st.toast("Post submitted and published to your Profile Wall! 🚀", icon="✅")
                            st.rerun()
                        else:
                            st.error("Failed to submit post.")
        else:
            st.info("👈 Select options on the left and click **Generate Personalized Content** to begin.")

# -----------------------------------------------------------------------------
# TAB 3: Personalization Dataset (RAG & Fine-Tuning)
# -----------------------------------------------------------------------------
with tab_dataset:
    st.markdown("#### 📚 Personalization Dataset Hub (ChromaDB Vector RAG)")
    st.caption(
        "Manage your personal writing samples. During generation, ChromaDB retrieves the top-2 most relevant "
        "examples as few-shot in-context learning anchors."
    )

    # Top Export Bar
    col_d1, col_d2 = st.columns([3, 1])
    with col_d1:
        st.markdown("##### 📥 Fine-Tuning Dataset Export")
        st.caption("Export your personal style dataset in JSONL format for parameter fine-tuning.")
    with col_d2:
        export_url = client.export_dataset_url()
        # Direct download helper
        samples_res = client.get_writing_samples(token=st.session_state.auth_token)
        samples_list = samples_res.get("data", {}).get("samples", []) if samples_res.get("status_code") == 200 else []
        history_res = client.get_content_history(token=st.session_state.auth_token)
        history_list = history_res.get("data", []) if history_res.get("status_code") == 200 else []

        jsonl_lines = []
        for s in samples_list:
            item = {"messages": [{"role": "user", "content": f"Write a {s.get('content_type')} titled '{s.get('title')}'"}, {"role": "assistant", "content": s.get("content")}]}
            jsonl_lines.append(json.dumps(item, ensure_ascii=False))
        for h in history_list:
            if h.get("rating", 0) >= 4 or h.get("saved_to_dataset"):
                item = {"messages": [{"role": "user", "content": f"Write a {h.get('content_type')} about: {h.get('prompt')}"}, {"role": "assistant", "content": h.get("generated_content")}]}
                jsonl_lines.append(json.dumps(item, ensure_ascii=False))

        dataset_export_str = "\n".join(jsonl_lines)
        st.download_button(
            "📥 Download JSONL Dataset",
            data=dataset_export_str,
            file_name=f"personalization_dataset_{st.session_state.user_info.get('username')}.jsonl",
            mime="application/x-ndjson",
            type="secondary",
            use_container_width=True,
        )

    st.divider()

    col_add, col_list = st.columns([1, 1], gap="large")

    with col_add:
        st.markdown("##### ➕ Add New Writing Sample")
        with st.form("add_sample_form"):
            s_title = st.text_input("Sample Title", placeholder="e.g. My Approach to Microservices")
            s_type = st.selectbox("Content Type", ["blog_post", "linkedin_post", "marketing_email", "article"])
            s_tags = st.text_input("Tags (comma-separated)", value="architecture, clean-code")
            s_content = st.text_area("Sample Text Content:", height=180, placeholder="Paste a high-performing post or article here...")
            add_sample_btn = st.form_submit_button("Index into ChromaDB ⚡", type="primary")

            if add_sample_btn:
                if not s_title or not s_content or len(s_content.strip()) < 10:
                    st.error("Please provide a title and at least 10 characters of content.")
                else:
                    tags_list = [t.strip() for t in s_tags.split(",") if t.strip()]
                    with st.spinner("Embedding and indexing sample..."):
                        s_res = client.post_writing_sample(
                            title=s_title,
                            content_type=s_type,
                            content=s_content,
                            tags=tags_list,
                            token=st.session_state.auth_token,
                        )
                        if s_res.get("status_code") in (200, 201):
                            st.success("Writing sample added and vectorized in ChromaDB!")
                            st.rerun()
                        else:
                            st.error(f"Failed to add sample: {s_res.get('data')}")

    with col_list:
        st.markdown(f"##### 🗂️ Active Style Samples ({len(samples_list)})")
        if not samples_list:
            st.info("No custom writing samples added yet. Add samples on the left or save 5-star generated posts.")
        else:
            for sample in samples_list:
                with st.expander(f"📌 {sample.get('title')} ({sample.get('content_type')})", expanded=False):
                    st.caption(f"Tags: {', '.join(sample.get('tags', []))} | Added: {sample.get('created_at', '')[:10]}")
                    st.text_area("Content", value=sample.get("content", ""), height=100, disabled=True, key=f"txt_{sample.get('id')}")
                    if st.button("🗑️ Delete Sample", key=f"del_{sample.get('id')}", type="secondary"):
                        del_res = client.delete_writing_sample(sample_id=sample.get("id"), token=st.session_state.auth_token)
                        if del_res.get("status_code") == 200:
                            st.success("Sample deleted.")
                            st.rerun()
                        else:
                            st.error("Failed to delete sample.")
