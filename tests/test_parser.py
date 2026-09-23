"""Tests for transcript parser."""

from pathlib import Path

import pytest

from src.parser import load_all_transcripts, parse_transcript, timestamp_to_seconds

FILES = Path(__file__).resolve().parent.parent / "Files"


def test_timestamp_to_seconds():
    assert timestamp_to_seconds("01:20") == 80
    assert timestamp_to_seconds("00:00") == 0


def test_segment_counts_all_transcripts():
    segments = load_all_transcripts(FILES)
    assert len(segments) == 42


def test_spot_check_france_expert_turn():
    path = FILES / "Transcript_1_France.txt"
    segments = parse_transcript(path)
    seg = next(s for s in segments if s.timestamp == "01:20")
    assert seg.speaker == "Dr. Martin"
    assert "capital budget approval" in seg.text
    assert seg.expert_name == "Dr. Jean Martin"
    assert seg.market == "France"
    assert seg.timestamp_seconds == 80


def test_spot_check_growth_quote_france():
    segments = parse_transcript(FILES / "Transcript_1_France.txt")
    seg = next(s for s in segments if s.timestamp == "05:07")
    assert "15 to 20 percent" in seg.text


def test_crlf_stripped():
    raw = (FILES / "Transcript_1_France.txt").read_bytes()
    assert b"\r\n" in raw
    segments = parse_transcript(FILES / "Transcript_1_France.txt")
    assert all("\r" not in s.text for s in segments)
