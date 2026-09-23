"""Tests for quote verification."""

from pathlib import Path

from src.parser import load_all_transcripts, parse_transcript
from src.verify import verify_quote, verify_quotes_from_response

FILES = Path(__file__).resolve().parent.parent / "Files"


def test_accepts_verbatim_quote():
    segments = parse_transcript(FILES / "Transcript_1_France.txt")
    quote = "The biggest issue is still capital budget approval."
    assert verify_quote(quote, segments, "01:20")


def test_rejects_paraphrased_quote():
    segments = parse_transcript(FILES / "Transcript_1_France.txt")
    fake = "The main problem is capital budget sign-off."
    assert not verify_quote(fake, segments, "01:20")


def test_verify_quotes_from_response_drops_bad():
    segments = parse_transcript(FILES / "Transcript_1_France.txt")
    quotes = [
        {"text": "Training matters, especially in the first year.", "timestamp": "03:10"},
        {"text": "Training is crucial in year one.", "timestamp": "03:10"},
    ]
    result = verify_quotes_from_response(quotes, segments)
    assert result[0].verified
    assert not result[1].verified
