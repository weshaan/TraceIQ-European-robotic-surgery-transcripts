"""Feature 2: cross-expert themes and disagreements from grounded answers."""

from __future__ import annotations

import json
from typing import Any, Callable

from src.llm import call_llm
from src.step_log import log_step

SYSTEM_PROMPT = """You synthesize expert interview answers. Use only the provided grounded answers and quotes.
Respond with valid JSON only."""


def build_synthesis_prompt(question: str, expert_answers: list[dict[str, Any]]) -> str:
    payload = []
    for row in expert_answers:
        payload.append(
            {
                "expert": row.get("expert"),
                "addressed": row.get("addressed"),
                "answer": row.get("answer"),
                "quotes": row.get("quotes") or [],
            }
        )
    return f"""Question: {question}

Grounded answers from three experts (each answer was produced using only that expert's transcript):

{json.dumps(payload, indent=2)}

Identify agreement and disagreement across experts using ONLY the information above.

Respond in this exact JSON format:
{{
  "question": "{question}",
  "agreements": [
    {{"summary": "...", "supporting": [{{"expert": "...", "timestamp": "..."}}]}}
  ],
  "disagreements": [
    {{"summary": "...", "positions": [{{"expert": "...", "position": "...", "timestamp": "..."}}]}}
  ]
}}

Rules:
- Every supporting entry must reference an expert and a timestamp from their quotes above.
- If experts gave different numeric or qualitative outlooks, surface that as disagreement.
- Do not add facts not present in the grounded answers.
"""


def synthesize_question(
    question: str,
    expert_answers: list[dict[str, Any]],
    *,
    client_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    user = build_synthesis_prompt(question, expert_answers)
    with log_step("llm synthesis", detail=question[:80]):
        parsed = call_llm(SYSTEM_PROMPT, user, client_factory=client_factory)
    parsed.setdefault("question", question)
    return parsed


def run_synthesis(
    grouped_answers: dict[str, list[dict[str, Any]]],
    questions: list[str],
    *,
    client_factory: Callable[[], Any] | None = None,
) -> list[dict[str, Any]]:
    with log_step("synthesis batch", detail=f"{len(questions)} questions"):
        out: list[dict[str, Any]] = []
        for q in questions:
            answers = grouped_answers.get(q, [])
            out.append(synthesize_question(q, answers, client_factory=client_factory))
        return out


def growth_outlook_disagreement_surfaced(synthesis_row: dict[str, Any]) -> bool:
    """Heuristic check for known Q5 disagreement (France / Germany / UK outlook)."""
    blob = json.dumps(synthesis_row).lower()
    markers = [
        "15",
        "20",
        "single digit",
        "double digit",
        "above 15",
        "high single",
        "low double",
    ]
    hits = sum(1 for m in markers if m in blob)
    disagreements = synthesis_row.get("disagreements") or []
    return hits >= 2 and len(disagreements) >= 1
