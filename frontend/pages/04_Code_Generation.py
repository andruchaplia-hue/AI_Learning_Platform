import json
import streamlit as st
from frontend.services.api_client import APIClient

st.set_page_config(
    page_title="UC4: Code Generation Assistant | AI Learning Platform",
    page_icon="💻",
    layout="wide",
)

st.title("💻 Use Case 4: Code Generation Assistant")
st.caption("Framework Target: Semantic Kernel Sequential Plugin Agents (Analyzer → Generator → Reviewer → Advisor)")

client = APIClient()

# Top System Status Bar
col_status1, col_status2, col_status3 = st.columns([1, 1, 2])
with col_status1:
    try:
        health = client.get_health()
        st.success(f"Backend Status: {health.get('status', 'ok').upper()}")
    except Exception:
        st.error("Backend Disconnected")

with col_status2:
    try:
        ver = client.get_version()
        st.info(f"Provider: {ver.get('provider', 'google').upper()}")
    except Exception:
        st.info("Provider: DEFAULT")

with col_status3:
    st.caption("Architecture: 5-Layer Clean Architecture | Multi-Agent Sequential Pipeline")

st.divider()

# 3 Main IDE Tabs
tab1, tab2, tab3 = st.tabs([
    "💻 Code Assistant & Model Switcher",
    "🔀 Git Context & Visual Diff Refactor",
    "🎓 Fine-Tuning Hub & Dataset Manager",
])

# ==============================================================================
# TAB 1: CODE ASSISTANT & MODEL SWITCHER
# ==============================================================================
with tab1:
    st.subheader("💻 IDE Natural Language Code Generator")
    st.markdown(
        "Generate production-ready code snippets with multi-step Semantic Kernel review and actionable suggestions."
    )

    col_input, col_config = st.columns([3, 1])

    with col_config:
        st.markdown("### ⚙️ Model Selection")
        model_mode_choice = st.radio(
            "Target Model",
            options=["Base Model (default)", "Fine-Tuned Model"],
            index=0,
            help="Choose between base Gemini model or code-fine-tuned model",
        )
        model_mode = "base" if "Base" in model_mode_choice else "tuned"

        compare_mode = st.checkbox(
            "⚡ Side-by-Side Comparison",
            value=False,
            help="Run prompt against BOTH Base and Fine-Tuned models simultaneously to compare output quality & speed.",
        )

        st.caption("Preset Prompts:")
        if st.button("Sample: FastAPI Endpoint"):
            st.session_state["prompt_input"] = "Create a FastAPI endpoint for user registration with email validation and error handling."
        if st.button("Sample: Unified Diff Helper"):
            st.session_state["prompt_input"] = "Write a Python function to compute unified diff between two text files using difflib."

    with col_input:
        prompt_text = st.text_area(
            "Natural Language Prompt / Requirement Description",
            value=st.session_state.get("prompt_input", ""),
            height=140,
            placeholder="e.g. Create a FastAPI health check endpoint with uptime tracking and memory metrics...",
        )
        generate_btn = st.button("⚡ Generate Code & Audit", type="primary", width="stretch")

    if generate_btn:
        if not prompt_text.strip():
            st.warning("Please enter a prompt requirement before generating.")
        else:
            if compare_mode:
                st.markdown("---")
                st.markdown("### 📊 Side-by-Side Model Comparison")
                col_base, col_tuned = st.columns(2)

                with col_base:
                    st.markdown("#### 🔵 Base Model")
                    with st.spinner("Executing Base Model SK Pipeline..."):
                        res_base = client.post_code_generation(prompt_text, model_mode="base")

                    if res_base.get("status_code") == 200 and res_base.get("data"):
                        data_b = res_base["data"]
                        st.success(f"Done in {data_b.get('execution_time_sec', 0)}s | Model: {data_b.get('model_used')}")
                        st.code(data_b.get("generated_code", ""), language="python")

                        with st.expander("🔍 Code Audit Report"):
                            st.markdown(data_b.get("review_comments", ""))

                        with st.expander("💡 Improvement Suggestions"):
                            for sug in data_b.get("suggestions", []):
                                st.markdown(f"- {sug}")
                    else:
                        st.error("Failed to generate code with Base Model.")

                with col_tuned:
                    st.markdown("#### 🟢 Fine-Tuned Model")
                    with st.spinner("Executing Fine-Tuned Model SK Pipeline..."):
                        res_tuned = client.post_code_generation(prompt_text, model_mode="tuned")

                    if res_tuned.get("status_code") == 200 and res_tuned.get("data"):
                        data_t = res_tuned["data"]
                        st.success(f"Done in {data_t.get('execution_time_sec', 0)}s | Model: {data_t.get('model_used')}")
                        st.code(data_t.get("generated_code", ""), language="python")

                        with st.expander("🔍 Code Audit Report"):
                            st.markdown(data_t.get("review_comments", ""))

                        with st.expander("💡 Improvement Suggestions"):
                            for sug in data_t.get("suggestions", []):
                                st.markdown(f"- {sug}")
                    else:
                        raw_err = res_tuned.get("raw_response")
                        err_msg = res_tuned.get("data", {}).get("message") if res_tuned.get("data") else "Fine-tuned model unavailable."
                        st.error(f"Fine-Tuned Model Error ({res_tuned.get('status_code')}): {err_msg}")
            else:
                with st.spinner(f"Executing SK Agent Pipeline using {model_mode.upper()} model..."):
                    res = client.post_code_generation(prompt_text, model_mode=model_mode)

                if res.get("status_code") == 200 and res.get("data"):
                    data = res["data"]
                    st.markdown("---")
                    col_res_header, col_res_meta = st.columns([3, 1])

                    with col_res_header:
                        st.subheader("📦 Generated Code Snippet")
                    with col_res_meta:
                        st.metric("Execution Time", f"{data.get('execution_time_sec', 0)}s")
                        st.caption(f"Model: {data.get('model_used')}")


                    # Code Output
                    code = data.get("generated_code", "")
                    st.code(code, language="python")
                    st.download_button(
                        label="💾 Download Code (.py)",
                        data=code,
                        file_name="generated_code.py",
                        mime="text/x-python",
                    )

                    # Review and Suggestions
                    col_review, col_sug = st.columns(2)
                    with col_review:
                        st.markdown("### 🔍 Semantic Kernel Audit Report")
                        st.info(data.get("review_comments", "Audit completed."))

                    with col_sug:
                        st.markdown("### 💡 Actionable Suggestions")
                        for idx, sug in enumerate(data.get("suggestions", []), 1):
                            st.checkbox(f"{idx}. {sug}", value=False, key=f"sug_{idx}")
                else:
                    raw_err = res.get("raw_response")
                    err_msg = res.get("data", {}).get("message") if isinstance(res.get("data"), dict) and res.get("data", {}).get("message") else "Backend API call failed."
                    st.error(f"Generation Error ({res.get('status_code')}): {err_msg}")



# ==============================================================================
# TAB 2: GIT CONTEXT & VISUAL DIFF REFACTORING
# ==============================================================================
with tab2:
    st.subheader("🔀 Git Refactoring & Visual Diff Engine")
    st.markdown(
        "Paste existing source file content, describe your refactoring goal, and inspect visual unified code diffs."
    )

    col_target, col_ref_prompt = st.columns(2)

    sample_code = """from fastapi import APIRouter

router = APIRouter()

@router.get("/users")
def get_users():
    return [{"id": 1, "name": "Alice"}]
"""

    with col_target:
        filename_input = st.text_input("Target File Name", value="routes/users.py")
        original_code = st.text_area(
            "Original Source Code Content",
            value=sample_code,
            height=200,
        )

    with col_ref_prompt:
        refactor_instruction = st.text_area(
            "Refactoring Instruction",
            value="Add async DB session handling, Pydantic response model, and error logging.",
            height=150,
        )
        diff_model_choice = st.radio("Model", ["Base Model", "Fine-Tuned Model"], key="diff_model")
        diff_model = "base" if "Base" in diff_model_choice else "tuned"
        refactor_btn = st.button("🔀 Generate Visual Unified Diff", type="primary", width="stretch")

    if refactor_btn:
        if not original_code.strip() or not refactor_instruction.strip():
            st.warning("Please provide both original source code and refactoring instruction.")
        else:
            with st.spinner("Computing refactored version and unified diff..."):
                res_diff = client.post_code_diff(
                    prompt=refactor_instruction,
                    target_filename=filename_input,
                    target_file_content=original_code,
                    model_mode=diff_model,
                )

            if res_diff.get("status_code") == 200 and res_diff.get("data"):
                diff_data = res_diff["data"]
                st.markdown("---")
                st.subheader("📊 Visual Diff Output")

                diff_text = diff_data.get("diff")
                if diff_text:
                    st.code(diff_text, language="diff")
                else:
                    st.info("No line differences detected between original and refactored code.")

                st.subheader("✨ Refactored Code Output")
                refactored = diff_data.get("generated_code", "")
                st.code(refactored, language="python")

                st.download_button(
                    label=f"💾 Download Refactored {filename_input}",
                    data=refactored,
                    file_name=filename_input.split("/")[-1],
                    mime="text/x-python",
                )
            else:
                st.error("Failed to compute refactoring diff.")


# ==============================================================================
# TAB 3: FINE-TUNING HUB & DATASET MANAGER
# ==============================================================================
with tab3:
    st.subheader("🎓 Fine-Tuning Hub & Dataset Manager")
    st.markdown(
        "Inspect training pairs, add new JSONL training examples, and monitor fine-tuning model job status."
    )

    # Job status container
    col_job1, col_job2 = st.columns([2, 1])
    with col_job1:
        st.markdown("### 📡 Fine-Tuned Model Job Status")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🔄 Check Status"):
                st.rerun()
        with col_b2:
            trigger_job_btn = st.button("🚀 Trigger Fine-Tuning Job", type="primary")

        if trigger_job_btn:
            with st.spinner("Uploading JSONL dataset and submitting Google GenAI Fine-Tuning job..."):
                job_info = client.trigger_fine_tune_job()
            if job_info.get("status_code") == 200 and job_info.get("data"):
                jdata = job_info["data"]
                st.success(f"🚀 Fine-Tuning Job Submitted! Target Model: `{jdata.get('tuned_model_id')}`")
                st.info(jdata.get("message", "Job is training on Google Cloud GPU infrastructure."))
            else:
                err_msg = job_info.get("data", {}).get("message") if isinstance(job_info.get("data"), dict) and job_info.get("data", {}).get("message") else "Could not trigger fine-tuning job."
                st.error(f"❌ Fine-Tuning Submission Status ({job_info.get('status_code', 500)}): {err_msg}")
        else:
            job_info = client.get_code_gen_dataset()
            # Fetch status via client
            try:
                status_res = client.trigger_fine_tune_job()
                if status_res.get("status_code") == 200 and status_res.get("data"):
                    jdata = status_res["data"]
                    active_model = jdata.get("tuned_model_id") or "None (Not Trained Yet)"
                    if jdata.get("tuned_model_id"):
                        st.success(f"Dataset Size: **{jdata.get('dataset_size', 0)} examples** | Active Model: `{active_model}`")
                    else:
                        st.info(f"Dataset Size: **{jdata.get('dataset_size', 0)} examples** | Active Model: `{active_model}`")
                    st.caption(jdata.get("message", ""))
                else:
                    st.warning("Fine-Tuning Hub initialized. No active fine-tuned model trained yet.")
            except Exception:
                st.caption("Ready for fine-tuning submission.")





    st.divider()

    st.markdown("### 📝 Add New Fine-Tuning Training Pair")
    with st.form("add_pair_form"):
        new_prompt = st.text_input("User Prompt Requirement", placeholder="e.g. Create Pydantic model for JWT payload")
        new_code = st.text_area("Expected Assistant Code Response", placeholder="class JWTPayload(BaseModel):\n    sub: str\n    exp: int")
        submit_pair = st.form_submit_button("➕ Add Example to Dataset")

        if submit_pair:
            if not new_prompt.strip() or not new_code.strip():
                st.warning("Both prompt and expected code are required.")
            else:
                add_res = client.post_code_gen_dataset(new_prompt, new_code)
                if add_res.get("status_code") in (200, 201):
                    st.success("New training pair successfully added to JSONL dataset!")
                    st.rerun()
                else:
                    st.error("Failed to add entry to dataset.")

    st.divider()

    st.markdown("### 📋 Training Dataset Pairs (`data/fine_tuning/code_generation_dataset.jsonl`)")
    dataset_res = client.get_code_gen_dataset()
    if dataset_res.get("status_code") == 200 and dataset_res.get("data"):
        ds_data = dataset_res["data"]
        entries = ds_data.get("entries", [])
        st.markdown(f"Total Validated Examples: **{ds_data.get('total_entries', 0)}**")

        for entry in entries:
            with st.expander(f"Example #{entry.get('id')}: {entry.get('user_prompt')[:70]}..."):
                st.markdown("**User Prompt:**")
                st.info(entry.get("user_prompt"))
                st.markdown("**Expected Code:**")
                st.code(entry.get("expected_code"), language="python")
    else:
        st.warning("No dataset entries found or failed to load dataset.")
