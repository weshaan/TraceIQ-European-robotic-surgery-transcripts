"""Integration-style tests with mocked LLM."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.chat import chat_answer, single_expert_attribution
from src.parser import load_all_transcripts, load_interview_questions
from src.qa_per_expert import answer_question_for_expert
from src.retrieval import TranscriptRetriever
from src.synthesis import (
    build_synthesis_prompt,
    growth_outlook_disagreement_surfaced,
    synthesize_question,
)

FILES = Path(__file__).resolve().parent.parent / "Files"


@pytest.fixture(scope="module")
def retriever():
    return TranscriptRetriever(load_all_transcripts(FILES))


def test_no_relevant_retrieval_returns_not_addressed(retriever):
    """When retrieval is empty / irrelevant, skip LLM and mark not addressed."""
    from unittest.mock import patch

    with (
        patch.object(retriever, "search", return_value=([], [])),
        patch.object(retriever, "has_relevant_hits", return_value=False),
    ):
        out = answer_question_for_expert(
            retriever,
            "What is the weather in Paris?",
            "Dr. Jean Martin",
            "Head of Urology",
            "France",
            client_factory=lambda: MagicMock(),
        )
    assert out["addressed"] is False
    assert "Not addressed" in out["answer"]


def test_llm_not_addressed_when_model_says_so(retriever):
    from unittest.mock import patch

    with (
        patch(
            "src.qa_per_expert.call_llm",
            return_value={
                "answer": "The excerpts do not discuss this topic.",
                "quotes": [],
                "addressed": False,
            },
        ),
    ):
        out = answer_question_for_expert(
            retriever,
            "What is the hospital's favorite color?",
            "Dr. Jean Martin",
            "Head of Urology",
            "France",
        )
    assert out["addressed"] is False
    assert out["quotes"] == []


def test_synthesis_surfaces_growth_disagreement():
    q5 = "What adoption trend do you expect over the next 3–5 years?"
    expert_answers = [
        {
            "expert": "Dr. Jean Martin",
            "addressed": True,
            "answer": "Steady growth, 15–20% in stronger centres.",
            "quotes": [{"text": "maybe 15 to 20 percent more procedures annually", "timestamp": "05:07"}],
        },
        {
            "expert": "Anna Keller",
            "addressed": True,
            "answer": "High single digits or low double digits, not ~20%.",
            "quotes": [
                {
                    "text": "probably closer to high single digits or low double digits",
                    "timestamp": "05:08",
                }
            ],
        },
        {
            "expert": "Dr. Emily Carter",
            "addressed": True,
            "answer": "Could exceed 15% if training expands.",
            "quotes": [{"text": "procedure growth above 15 percent annually", "timestamp": "04:06"}],
        },
    ]

    prompt = build_synthesis_prompt(q5, expert_answers)
    assert "15 to 20 percent" in prompt
    assert "high single digits" in prompt
    assert "above 15 percent" in prompt

    mock_response = {
        "question": q5,
        "agreements": [
            {
                "summary": "All expect continued growth, not explosive.",
                "supporting": [{"expert": "Dr. Jean Martin", "timestamp": "05:07"}],
            }
        ],
        "disagreements": [
            {
                "summary": "Magnitude differs: France ~15–20%, Germany high single/low double digits, UK above 15%.",
                "positions": [
                    {"expert": "Dr. Jean Martin", "position": "15–20%", "timestamp": "05:07"},
                    {"expert": "Anna Keller", "position": "high single/low double digits", "timestamp": "05:08"},
                    {"expert": "Dr. Emily Carter", "position": "above 15%", "timestamp": "04:06"},
                ],
            }
        ],
    }

    def factory():
        client = MagicMock()
        client.messages.create.return_value = MagicMock(
            content=[MagicMock(text=str(mock_response).replace("'", '"'))]
        )
        return client

    # Use direct mock on call_llm level — synthesize with injected JSON via patch
    from unittest.mock import patch

    with patch("src.synthesis.call_llm", return_value=mock_response):
        result = synthesize_question(q5, expert_answers)

    assert growth_outlook_disagreement_surfaced(result)


def test_chat_attributes_single_expert_topic(retriever):
    mock_json = {
        "answer": "Germany procurement often takes nine to eighteen months.",
        "quotes": [
            {
                "text": "Nine to eighteen months is common.",
                "timestamp": "06:05",
                "expert": "Anna Keller",
            }
        ],
        "addressed": True,
    }

    from unittest.mock import patch

    with patch("src.chat.call_llm", return_value=mock_json):
        result = chat_answer(
            retriever,
            "How long does procurement take in Germany?",
            top_k=8,
        )

    assert result["addressed"]
    assert len(result["quotes"]) == 1
    assert result["quotes"][0]["expert"] == "Anna Keller"
    assert single_expert_attribution(result["quotes"]) == "Anna Keller"
