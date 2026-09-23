"""Streamlit entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import streamlit as st

from src.chat import chat_answer
from src.parser import load_all_transcripts, load_interview_questions
from src.qa_per_expert import run_per_expert_qa_for_question
from src.retrieval import TranscriptRetriever
from src.llm import get_model, llm_is_configured
from src.synthesis import synthesize_question
from src.step_log import log_step, setup_pipeline_logging
from src.ui import (
    expert_card_html,
    footer_hint,
    hint,
    inject_theme,
    panel_header,
    render_header,
    render_utility_bar,
    sidebar,
    synthesis_html,
)

FILES_DIR = ROOT / "Files"
GUIDE_PATH = FILES_DIR / "Interview_Guide.txt"
CHROMA_DIR = ROOT / ".cache" / "chroma"
RETRIEVER_CACHE_KEY = 1


@st.cache_resource(show_spinner="Loading transcript index…")
def get_retriever() -> TranscriptRetriever:
    with log_step("build retriever (cached resource)"):
        segments = load_all_transcripts(FILES_DIR)
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        return TranscriptRetriever(segments, persist_dir=CHROMA_DIR)


@st.cache_data(show_spinner=False)
def get_questions() -> list[str]:
    return load_interview_questions(GUIDE_PATH)


@st.cache_data(show_spinner="Generating answers…")
def get_per_expert_for_question(
    _retriever_id: int, question: str, _model: str
) -> list[dict]:
    with log_step("streamlit cache: per-expert for question", detail=question[:80]):
        return run_per_expert_qa_for_question(get_retriever(), question)


@st.cache_data(show_spinner="Synthesizing…")
def get_synthesis_for_question(
    _retriever_id: int, question: str, _model: str
) -> dict:
    with log_step("streamlit cache: synthesis for question", detail=question[:80]):
        answers = get_per_expert_for_question(_retriever_id, question, _model)
        return synthesize_question(question, answers)


def _expert_meta(retriever: TranscriptRetriever, expert_name: str) -> tuple[str, str]:
    for seg in retriever.segments:
        if seg.expert_name == expert_name:
            return seg.expert_role, seg.market
    return "", ""


def _sort_expert_rows(retriever: TranscriptRetriever, rows: list[dict]) -> list[dict]:
    market_order = {"France": 0, "Germany": 1, "United Kingdom": 2}
    return sorted(
        rows,
        key=lambda r: market_order.get(
            next(
                (s.market for s in retriever.segments if s.expert_name == r.get("expert")),
                "",
            ),
            99,
        ),
    )


def main() -> None:
    setup_pipeline_logging()
    st.set_page_config(
        page_title="Transcript Studio",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()

    model_id = get_model()
    api_ok = llm_is_configured()

    try:
        retriever = get_retriever()
        questions = get_questions()
    except Exception as e:
        st.error(f"Failed to load transcripts: {e}")
        return

    sidebar(api_ok)
    render_utility_bar(api_ok)
    render_header(
        "Per-market grounded answers, synthesis, and Q&A on expert interviews.",
    )

    tab1, tab2, tab3 = st.tabs(["Per expert", "Synthesis", "Chat"])

    with tab1:
        panel_header("👤", "Per expert", "Interview guide")
        q_pick = st.selectbox("Question", questions, key="tab1_q", label_visibility="collapsed")

        rows: list[dict] = []
        if api_ok:
            if st.session_state.get("tab1_loaded_question") == q_pick:
                try:
                    rows = get_per_expert_for_question(
                        RETRIEVER_CACHE_KEY, q_pick, model_id
                    )
                    rows = _sort_expert_rows(retriever, rows)
                except Exception as e:
                    st.error(f"Could not generate answers: {e}")
            else:
                if st.button("Generate answers", type="primary"):
                    st.session_state.tab1_loaded_question = q_pick
                    st.rerun()
        else:
            hint("Add OPENROUTER_API_KEY to `.env` to enable generation.")

        if rows:
            st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
            cols = st.columns(3, gap="medium")
            for col, row in zip(cols, rows):
                expert = row.get("expert", "Expert")
                role, market = _expert_meta(retriever, expert)
                addressed = bool(row.get("addressed"))
                answer = (row.get("answer") or "").strip()
                if not addressed:
                    answer = answer or "Not addressed in this transcript."
                with col:
                    st.markdown(
                        expert_card_html(
                            expert=expert,
                            role=role,
                            market=market,
                            addressed=addressed,
                            answer=answer,
                            quotes=row.get("quotes") or [],
                            quote_flags=row.get("quote_flags") or [],
                        ),
                        unsafe_allow_html=True,
                    )
        footer_hint("Generated answer shows here.")

    with tab2:
        panel_header("◆", "Synthesis", "Themes & disagreements")
        q_synth = st.selectbox(
            "Question", questions, key="tab2_q", label_visibility="collapsed"
        )

        synth_block: dict | None = None
        if api_ok:
            if st.session_state.get("tab2_loaded_question") == q_synth:
                try:
                    synth_block = get_synthesis_for_question(
                        RETRIEVER_CACHE_KEY, q_synth, model_id
                    )
                except Exception as e:
                    st.error(f"Synthesis failed: {e}")
            elif st.button("Run synthesis", type="primary", key="tab2_run"):
                st.session_state.tab2_loaded_question = q_synth
                st.rerun()
            else:
                hint("Uses cached per-expert answers from Tab 1 when available.")
        else:
            hint("Configure OpenRouter to run synthesis.")

        if synth_block:
            st.markdown(synthesis_html(synth_block), unsafe_allow_html=True)

    with tab3:
        panel_header("💬", "Chat", "Ask across transcripts")
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.write(msg.get("text", ""))
                for quote in msg.get("quotes") or []:
                    st.markdown(
                        f'> "{quote.get("text")}" — {quote.get("expert")}, '
                        f'{quote.get("timestamp")}'
                    )

        user_q = st.chat_input("Ask a question about the transcripts…")
        if user_q:
            st.session_state.chat_messages.append({"role": "user", "text": user_q})
            if not api_ok:
                st.session_state.chat_messages.append(
                    {"role": "assistant", "text": "API key not configured.", "quotes": []}
                )
            else:
                try:
                    result = chat_answer(retriever, user_q)
                    st.session_state.chat_messages.append(
                        {
                            "role": "assistant",
                            "text": result.get("answer_display")
                            or result.get("answer")
                            or "",
                            "quotes": result.get("quotes") or [],
                        }
                    )
                except Exception as e:
                    st.session_state.chat_messages.append(
                        {"role": "assistant", "text": f"Error: {e}", "quotes": []}
                    )
            st.rerun()


if __name__ == "__main__":
    main()
