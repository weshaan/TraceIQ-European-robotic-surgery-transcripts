"""Feature 3: free-form cross-transcript Q&A."""

from __future__ import annotations

from typing import Any, Callable

from src.llm import call_llm
from src.parser import Segment
from src.retrieval import TranscriptRetriever
from src.qa_per_expert import format_excerpts
from src.verify import verify_quotes_from_response
from src.step_log import log_step

SYSTEM_PROMPT = """You answer user questions using only transcript excerpts. Respond with valid JSON only."""

NOT_COVERED = "This isn't covered in the transcripts."


def build_chat_prompt(question: str, segments: list[Segment]) -> str:
    excerpts = format_excerpts(segments)
    return f"""Answer using ONLY the transcript excerpts below. Do not use outside knowledge.

User question: {question}

Transcript excerpts (expert name is in the segment metadata — attribute claims correctly):
{excerpts}

Respond in this exact JSON format:
{{
  "answer": "<answer with inline attribution, e.g. Dr. Martin said ...>",
  "quotes": [
    {{"text": "<verbatim substring>", "timestamp": "<MM:SS>", "expert": "<full expert name>"}}
  ],
  "addressed": true
}}

Rules:
- If excerpts do not support an answer, set "addressed": false and answer: "{NOT_COVERED}"
- Each quote must be verbatim from excerpts.
- When only one expert mentioned a topic, attribute only to that expert.
"""


def format_answer_with_citations(answer: str, quotes: list[dict[str, str]]) -> str:
    """Append citation markers for verified quotes."""
    if not quotes:
        return answer
    cites = []
    for q in quotes:
        expert = q.get("expert") or "Expert"
        ts = q.get("timestamp") or "?"
        cites.append(f"[{expert}, {ts}]")
    return f"{answer}\n\nCitations: {' '.join(cites)}"


def chat_answer(
    retriever: TranscriptRetriever,
    question: str,
    *,
    top_k: int = 8,
    client_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    with log_step("chat QA", detail=question[:80]):
        return _chat_answer_impl(
            retriever, question, top_k=top_k, client_factory=client_factory
        )


def _chat_answer_impl(
    retriever: TranscriptRetriever,
    question: str,
    *,
    top_k: int,
    client_factory: Callable[[], Any] | None,
) -> dict[str, Any]:
    segments, distances = retriever.search(question, top_k=top_k)

    if not retriever.has_relevant_hits(distances):
        return {
            "question": question,
            "answer": NOT_COVERED,
            "answer_display": NOT_COVERED,
            "quotes": [],
            "addressed": False,
            "quote_flags": [],
        }

    user = build_chat_prompt(question, segments)
    with log_step("llm chat answer"):
        parsed = call_llm(SYSTEM_PROMPT, user, client_factory=client_factory)

    addressed = bool(parsed.get("addressed", True))
    answer = (parsed.get("answer") or "").strip()
    if not addressed:
        answer = NOT_COVERED

    raw_quotes = parsed.get("quotes") or []
    with log_step("verify chat quotes"):
        vq = verify_quotes_from_response(
            [{"text": q.get("text"), "timestamp": q.get("timestamp")} for q in raw_quotes],
            segments,
        )

    expert_by_ts: dict[str, str] = {}
    for seg in segments:
        expert_by_ts[seg.timestamp] = seg.expert_name

    good_quotes: list[dict[str, str]] = []
    flags = []
    for i, v in enumerate(vq):
        expert = ""
        if i < len(raw_quotes):
            expert = (raw_quotes[i].get("expert") or "").strip()
        if not expert and v.timestamp in expert_by_ts:
            expert = expert_by_ts[v.timestamp]
        if v.verified:
            good_quotes.append(
                {"text": v.text, "timestamp": v.timestamp, "expert": expert}
            )
        else:
            flags.append(
                {
                    "text": v.text,
                    "timestamp": v.timestamp,
                    "note": v.verification_note,
                }
            )

    display = format_answer_with_citations(answer, good_quotes) if addressed else answer

    return {
        "question": question,
        "answer": answer,
        "answer_display": display,
        "quotes": good_quotes,
        "addressed": addressed,
        "quote_flags": flags,
    }


def single_expert_attribution(quotes: list[dict[str, str]]) -> str | None:
    """Return expert name if all quotes are from one expert."""
    names = {q.get("expert") for q in quotes if q.get("expert")}
    if len(names) == 1:
        return names.pop()
    return None
