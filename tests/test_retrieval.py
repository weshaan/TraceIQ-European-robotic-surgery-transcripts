"""Tests for retrieval layer."""

from pathlib import Path

import pytest

from src.parser import load_all_transcripts
from src.retrieval import TranscriptRetriever

FILES = Path(__file__).resolve().parent.parent / "Files"


@pytest.fixture(scope="module")
def retriever():
    segments = load_all_transcripts(FILES)
    return TranscriptRetriever(segments)


def test_search_finds_budget_topic(retriever):
    segs, dist = retriever.search(
        "capital budget approval ROI",
        top_k=3,
        expert_name="Dr. Jean Martin",
        market="France",
    )
    assert len(segs) >= 1
    timestamps = {s.timestamp for s in segs}
    assert "01:20" in timestamps or "02:18" in timestamps


def test_expert_filter_limits_market(retriever):
    segs, _ = retriever.search(
        "adoption robotic surgery",
        top_k=5,
        expert_name="Anna Keller",
        market="Germany",
    )
    assert all(s.expert_name == "Anna Keller" for s in segs)
    assert all(s.market == "Germany" for s in segs)


def test_cross_expert_search(retriever):
    segs, _ = retriever.search("surgeon training utilisation", top_k=6)
    markets = {s.market for s in segs}
    assert len(markets) >= 2
