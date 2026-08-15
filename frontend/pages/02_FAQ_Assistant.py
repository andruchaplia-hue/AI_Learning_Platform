import json
import time

import httpx
import streamlit as st

from frontend.components.common_widgets import apply_custom_theme, render_platform_sidebar
from frontend.services.api_client import APIClient


st.set_page_config(
    page_title="UC2: FAQ Chatbot | AI Learning Platform",
    page_icon="🤖",
    layout="wide",
)

apply_custom_theme()
api_client = APIClient()
render_platform_sidebar(api_client, active_module="FAQ Chatbot")

# Initialize session state for chat and execution logs
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"
if "last_execution_details" not in st.session_state:
    st.session_state.last_execution_details = None

# Header
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 class="main-title">🤖 Use Case 2: FAQ AI Chatbot</h1>
        <p class="sub-title">Semantic Kernel AI Agents with RAG Vector Retrieval & Decomposer Analysis</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Layout split: Left = Chat & Controls, Right = Agent Reasoning Log Inspection
col1, col2 = st.columns([1.2, 1.0], gap="large")

with col1:
    st.subheader("💬 Interactive Assistant")

    # Chat Options Bar: Clear chat history & User-Friendly Toggle & SK Filtering Toggle
    c_opts1, c_opts2, c_opts3 = st.columns([1.5, 1.5, 1.0])
    with c_opts1:
        user_friendly_toggle = st.toggle(
            "✨ User-Friendly Response",
            value=True,
            help="Enabled: LLM synthesizes and structures the answer. Disabled: returns direct raw FAQ text.",
        )
    with c_opts2:
        sk_filtering_toggle = st.toggle(
            "🔍 SK Agent Candidate Selection",
            value=True,
            help="Enabled: Semantic Kernel filters out irrelevant matches. Disabled: returns all matches above threshold.",
        )
    with c_opts3:
        if st.button("🗑️ Clear History", width="stretch"):
            st.session_state.messages = []
            st.session_state.last_execution_details = None
            st.session_state.session_id = f"session_{int(time.time())}"
            st.rerun()

    # Knowledge Base Management Expander
    with st.expander("📚 Knowledge Base Ingestion", expanded=False):
        tab1, tab2, tab3 = st.tabs([
            "➕ Add Item",
            "📥 json Import",
            "📝 Parse Text"
        ])

        # Mode 1: Single Q&A Entry
        with tab1:
            with st.form("add_single_faq_form"):
                f_cat = st.text_input("Category", value="General")
                f_q = st.text_input("Question")
                f_a = st.text_area("Answer")
                submitted = st.form_submit_button("Add & Index")
                if submitted:
                    if not f_q.strip() or not f_a.strip():
                        st.warning("Fields cannot be empty.")
                    else:
                        item_payload = {
                            "id": 0,
                            "category": f_cat.strip(),
                            "question": f_q.strip(),
                            "answer": f_a.strip(),
                        }
                        try:
                            res = api_client.post_faq_item(item_payload)
                            if res["status_code"] in (200, 201):
                                st.success("✅ FAQ Item added and vector store re-indexed!")
                            else:
                                st.error("Failed to add FAQ item.")
                        except httpx.ConnectError:
                            st.error("🔌 Backend is offline or initializing. Please try again in a few moments.")
                        except Exception as exc:
                            st.error(f"Unexpected error: {exc}")

        # Mode 2: Bulk Import JSON File
        with tab2:
            uploaded_file = st.file_uploader("Choose JSON File", type=["json"], key="m2_file")
            if uploaded_file is not None:
                try:
                    raw_content = uploaded_file.read().decode("utf-8")
                    json_data = json.loads(raw_content)
                    if isinstance(json_data, list) and len(json_data) > 0:
                        st.json(json_data[:2])
                        if st.button("📥 Import JSON", key="m2_btn"):
                            formatted_items = []
                            for idx, elem in enumerate(json_data, 1):
                                formatted_items.append({
                                    "id": elem.get("id", 0),
                                    "category": elem.get("category", "Imported"),
                                    "question": elem.get("question", "").strip(),
                                    "answer": elem.get("answer", "").strip(),
                                })
                            try:
                                res = api_client.post_faq_bulk(formatted_items)
                                if res["status_code"] in (200, 201):
                                    st.success(f"✅ Imported {len(formatted_items)} items successfully!")
                                else:
                                    st.error("Failed to import JSON items.")
                            except httpx.ConnectError:
                                st.error("🔌 Backend is offline or initializing. Please try again in a few moments.")
                            except Exception as exc:
                                st.error(f"Unexpected error: {exc}")
                    else:
                        st.warning("JSON file must be a non-empty list.")
                except Exception as exc:
                    st.error(f"Invalid JSON: {exc}")

        # Mode 3: Unstructured Raw Text Parsing
        with tab3:
            st.caption("Paste raw Q&A text. The platform will structure and index it.")
            raw_text_input = st.text_area(
                "Raw text:",
                height=130,
                placeholder="Past you are faq raw text here",
                key="m3_text",
            )
            if st.button("📝 Parse Raw Text", key="m3_btn"):
                if not raw_text_input.strip():
                    st.warning("Text cannot be empty.")
                else:
                    with st.spinner("Extracting FAQs..."):
                        try:
                            res = api_client.post_faq_parse_text(raw_text_input.strip())
                            if res["status_code"] in (200, 201) and res["data"]:
                                count = res["data"].get("extracted_count", 0)
                                items = res["data"].get("items", [])
                                st.success(f"✅ Indexed {count} FAQ items!")
                                if items:
                                    st.json(items)
                            else:
                                st.error("Extraction failed.")
                        except httpx.ConnectError:
                            st.error("🔌 Backend is offline or initializing. Please try again in a few moments.")
                        except Exception as exc:
                            st.error(f"Unexpected error: {exc}")

    # Render chat message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle user prompt input
    prompt_input = st.chat_input("Ask a question (e.g., 'What camera do I need?')")

    if prompt_input:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt_input})
        with st.chat_message("user"):
            st.markdown(prompt_input)

        # Call FastAPI Backend via APIClient with user_friendly and sk_filtering flags
        with st.chat_message("assistant"):
            mode_label = "User-Friendly" if user_friendly_toggle else "Direct Raw"
            filter_label = "SK Filter ON" if sk_filtering_toggle else "SK Filter OFF"
            with st.spinner(f"Agent executing ({mode_label} | {filter_label})..."):
                try:
                    response = api_client.post_faq_chat(
                        query=prompt_input,
                        session_id=st.session_state.session_id,
                        user_friendly=user_friendly_toggle,
                        sk_filtering=sk_filtering_toggle,
                    )

                    if response["status_code"] == 200 and response["data"]:
                        data = response["data"]
                        answer = data.get("answer", "No answer received.")
                        st.markdown(answer)

                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        st.session_state.last_execution_details = data.get("execution_details")
                        st.rerun()
                    else:
                        err_msg = "Error contacting backend API."
                        if response.get("raw_response"):
                            try:
                                err_msg = response["raw_response"].json().get("message", err_msg)
                            except Exception:
                                pass
                        st.error(f"❌ {err_msg}")
                        st.session_state.messages.append({"role": "assistant", "content": f"❌ {err_msg}"})
                except httpx.ConnectError:
                    err_offline = "🔌 Backend service is currently offline or indexing its database. Please wait a few seconds and try again."
                    st.error(err_offline)
                    st.session_state.messages.append({"role": "assistant", "content": err_offline})
                except Exception as exc:
                    st.error(f"Unexpected error: {exc}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {exc}"})


# Right Column: Reasoning & Execution Log Inspector
with col2:
    st.subheader("🔍 Agent Reasoning & Execution Log")
    details = st.session_state.last_execution_details

    if details:
        # Execution Summary Badge
        is_uf = details.get("user_friendly", True)
        is_filter = details.get("sk_filtering", True)
        mode_str = "✨ User-Friendly LLM" if is_uf else "📌 Direct Raw FAQ"
        filter_str = "🔍 SK Filter ON" if is_filter else "🔓 SK Filter OFF"
        exec_time = details.get("execution_time_seconds", 0.0)

        st.info(f"⏱️ **Time:** `{exec_time}s` | **Mode:** `{mode_str}` | **Filter:** `{filter_str}`")

        # 1. Query Decomposition Stage Log
        st.markdown("#### 1. 🧩 Query Decomposition (`DecomposerPlugin`)")
        if details.get("decomposer_fallback", False):
            st.warning("⚠️ **Decomposer Fallback**: Plugin failed. Used original query directly.")
        
        sub_queries = details.get("decomposed_queries", [])
        if sub_queries:
            for i, q in enumerate(sub_queries, 1):
                st.markdown(f"- **Sub-query #{i}:** `{q}`")
        else:
            st.caption("No sub-queries decomposed.")

        # 2. Vector Search Matching Log
        st.markdown("#### 2. 🎯 Matched FAQ Entries (`FAQPlugin` + ChromaDB)")
        faqs = details.get("retrieved_faqs", [])
        selected_ids = details.get("selected_faq_ids", [])
        
        if faqs:
            for item in faqs:
                score = item.get("score", 0.0)
                # Show status badge based on whether this item was selected by SK Agent and passed similarity threshold
                is_selected = (item.get("id") in selected_ids) if (is_filter and selected_ids) else True
                badge = "🟢 [SELECTED]" if (is_selected and score >= 0.4) else "🔴 [FILTERED OUT]"
                
                with st.expander(f"{badge} FAQ #{item.get('id')} - {item.get('question')[:40]}... (Sim: {score:.2f})"):
                    st.markdown(f"**Category:** `{item.get('category')}`")
                    st.markdown(f"**Question:** {item.get('question')}")
                    st.markdown(f"**Answer:** {item.get('answer')}")
        else:
            st.warning("No FAQ matches retrieved from vector store.")

        # 3. Coverage Analysis Stage Log
        st.markdown("#### 3. 📊 Coverage Analysis (`CoverageAnalyzerPlugin`)")
        max_sim = details.get("max_similarity_score", 0.0)
        cov_score = details.get("coverage_score", 0.0)
        missing_qs = details.get("missing_questions", [])
        cov_fallback = details.get("coverage_fallback", False)
        pipeline_err = details.get("pipeline_error")

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("Max Similarity", f"{max_sim:.2f}")
        with m_col2:
            if cov_fallback:
                st.metric("Sub-Query Coverage", "Error / Fallback", help="Coverage Plugin evaluation failed")
            elif cov_score == 1.0 and not selected_ids and not missing_qs:
                st.metric("Sub-Query Coverage", "Skipped", help="LLM unavailable / skipped")
            else:
                st.metric("Sub-Query Coverage", f"{cov_score * 100:.0f}%")

        if cov_fallback:
            st.error(f"❌ **Coverage Analyzer Failure**: {pipeline_err}")
            st.caption("ℹ️ **Fallback Applied**: Bypassed strict coverage checks. Used similarity score thresholds.")
        elif cov_score == 1.0 and not selected_ids and not missing_qs:
            st.caption("ℹ️ **LLM bypassed / offline**: Skipped LLM evaluation. Fallback vector threshold applied.")
        else:
            if missing_qs:
                st.warning(f"⚠️ Unanswered sub-questions: {', '.join(missing_qs)}")

        # 4. Final Response Mode
        st.markdown("#### 4. ⚙️ Output Generation Mode")
        if details.get("is_fallback", False):
            st.warning("⚠️ **Fallback Triggered**: Low similarity or coverage score. Response blocked.")
        elif is_uf:
            st.success("✨ **User-Friendly Mode Active**: Synthesized response covering all matched FAQ entries.")
        else:
            st.info("📌 **Raw FAQ Mode Active**: Displayed exact text from matched FAQ items without LLM synthesis.")

    else:
        st.caption(
            "Send a query in the chat to inspect query decomposition, vector search similarity scores, and SK Agent tool execution details."
        )
