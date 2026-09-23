"""Feature 1: per-expert interview-guide answers with grounding."""

from __future__ import annotations

from typing import Any, Callable

from src.llm import call_llm
from src.step_log import log_step
from src.parser import Segment
from src.retrieval import TranscriptRetriever
from src.verify import verify_quotes_from_response

SYSTEM_PROMPT = """You analyze research interview transcripts. Respond only with valid JSON, no markdown."""


def format_excerpts(segments: list[Segment]) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(
            f"{i}. [{seg.timestamp}] {seg.speaker}: {seg.text}"
        )
    return "\n".join(lines)


def build_user_prompt(
    expert_name: str,
    expert_role: str,
    market: str,
    question: str,
    segments: list[Segment],
) -> str:
    excerpts = format_excerpts(segments)
    return f"""You are analyzing a research interview transcript. Answer using ONLY the
transcript excerpts provided below. Do not use outside knowledge. Do not
infer beyond what is stated.

Expert: {expert_name} ({expert_role}, {market})
Question: {question}

Transcript excerpts (each tagged with its timestamp):
{excerpts}

Respond in this exact JSON format:
{{
  "answer": "<concise answer in your own words, 1-3 sentences>",
  "quotes": [{{"text": "<verbatim quote from the excerpts above, unmodified>", "timestamp": "<MM:SS>"}}],
  "addressed": true
}}

Rules:
- If the excerpts do not address the question, set "addressed": false and
  explain that briefly in "answer".
- Every "text" in "quotes" MUST be an exact, word-for-word substring of one of
  the excerpts above. Do not paraphrase inside quotes.
- Do not include information not present in the excerpts.
"""


def answer_question_for_expert(
    retriever: TranscriptRetriever,
    question: str,
    expert_name: str,
    expert_role: str,
    market: str,
    *,
    top_k: int = 6,
    client_factory: Callable[[], Any] | None = None,
    retry_on_bad_quotes: bool = True,
) -> dict[str, Any]:
    with log_step(
        "per-expert QA",
        detail=f"{expert_name} ({market})",
    ):
        return _answer_question_for_expert_impl(
            retriever,
            question,
            expert_name,
            expert_role,
            market,
            top_k=top_k,
            client_factory=client_factory,
            retry_on_bad_quotes=retry_on_bad_quotes,
        )


def _answer_question_for_expert_impl(
    retriever: TranscriptRetriever,
    question: str,
    expert_name: str,
    expert_role: str,
    market: str,
    *,
    top_k: int,
    client_factory: Callable[[], Any] | None,
    retry_on_bad_quotes: bool,
) -> dict[str, Any]:
    segments, distances = retriever.search(
        question, top_k=top_k, expert_name=expert_name, market=market
    )

    if not retriever.has_relevant_hits(distances):
        return {
            "question": question,
            "expert": expert_name,
            "answer": "Not addressed in this transcript.",
            "quotes": [],
            "addressed": False,
            "quote_flags": [],
        }

    user = build_user_prompt(expert_name, expert_role, market, question, segments)
    with log_step("llm per-expert answer", detail=expert_name):
        parsed = call_llm(SYSTEM_PROMPT, user, client_factory=client_factory)

    for attempt in range(2 if retry_on_bad_quotes else 1):
        with log_step("verify quotes", detail=expert_name):
            vq = verify_quotes_from_response(parsed.get("quotes") or [], segments)
        bad = [q for q in vq if not q.verified]
        if not bad or attempt == 1:
            break
        user_retry = user + "\n\nYour previous quotes were not verbatim. Copy exact substrings only."
        with log_step("llm quote retry", detail=expert_name):
            parsed = call_llm(SYSTEM_PROMPT, user_retry, client_factory=client_factory)

    addressed = bool(parsed.get("addressed", True))
    answer = (parsed.get("answer") or "").strip()
    if not addressed:
        answer = answer or "Not addressed in this transcript."

    good_quotes = [
        {"text": q.text, "timestamp": q.timestamp}
        for q in vq
        if q.verified
    ]
    flags = [
        {"text": q.text, "timestamp": q.timestamp, "note": q.verification_note}
        for q in vq
        if not q.verified
    ]

    return {
        "question": question,
        "expert": expert_name,
        "answer": answer,
        "quotes": good_quotes,
        "addressed": addressed,
        "quote_flags": flags,
        "retrieved_segment_ids": [s.segment_id for s in segments],
    }


def iter_experts(retriever: TranscriptRetriever) -> list[tuple[str, str, str]]:
    """(expert_name, role, market) sorted by market."""
    experts: dict[tuple[str, str], tuple[str, str]] = {}
    for seg in retriever.segments:
        key = (seg.expert_name, seg.market)
        if key not in experts:
            experts[key] = (seg.expert_role, seg.market)
    return [
        (expert_name, role, market)
        for (expert_name, market), (role, _) in sorted(experts.items(), key=lambda x: x[0][1])
    ]


def run_per_expert_qa_for_question(
    retriever: TranscriptRetriever,
    question: str,
    *,
    client_factory: Callable[[], Any] | None = None,
) -> list[dict[str, Any]]:
    with log_step("per-expert QA batch", detail=question[:80]):
        return _run_per_expert_qa_for_question_impl(
            retriever, question, client_factory=client_factory
        )


def _run_per_expert_qa_for_question_impl(
    retriever: TranscriptRetriever,
    question: str,
    *,
    client_factory: Callable[[], Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        answer_question_for_expert(
            retriever,
            question,
            expert_name,
            role,
            market,
            client_factory=client_factory,
        )
        for expert_name, role, market in iter_experts(retriever)
    ]


def run_all_per_expert_qa(
    retriever: TranscriptRetriever,
    questions: list[str],
    *,
    client_factory: Callable[[], Any] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for question in questions:
        results.extend(
            run_per_expert_qa_for_question(
                retriever, question, client_factory=client_factory
            )
        )
    return results


def group_answers_by_question(
    per_expert_results: list[dict[str, Any]],
    questions: list[str],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {q: [] for q in questions}
    for row in per_expert_results:
        q = row.get("question")
        if q in grouped:
            grouped[q].append(row)
    return grouped
