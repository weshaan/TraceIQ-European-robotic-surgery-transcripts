"""Quote verification against original segment text."""

from __future__ import annotations

from dataclasses import dataclass

from src.parser import Segment

# Documented policy: case-insensitive substring match on normalized whitespace.
CASE_SENSITIVE = False


def _normalize(text: str) -> str:
    return " ".join(text.split())


def find_quote_segment(quote_text: str, segments: list[Segment], timestamp: str | None) -> Segment | None:
    """Find the segment that should contain this quote (prefer matching timestamp)."""
    candidates = segments
    if timestamp:
        by_ts = [s for s in segments if s.timestamp == timestamp]
        if by_ts:
            candidates = by_ts
    q = _normalize(quote_text)
    for seg in candidates:
        hay = seg.text if CASE_SENSITIVE else seg.text.lower()
        needle = q if CASE_SENSITIVE else q.lower()
        if needle in hay:
            return seg
    if timestamp:
        for seg in segments:
            hay = seg.text if CASE_SENSITIVE else seg.text.lower()
            needle = q if CASE_SENSITIVE else q.lower()
            if needle in hay:
                return seg
    return None


def verify_quote(quote_text: str, segments: list[Segment], timestamp: str | None = None) -> bool:
    return find_quote_segment(quote_text, segments, timestamp) is not None


@dataclass
class VerifiedQuote:
    text: str
    timestamp: str
    verified: bool
    verification_note: str | None = None


def verify_quotes_from_response(
    quotes: list[dict],
    context_segments: list[Segment],
) -> list[VerifiedQuote]:
    """Verify each quote; drop unverified with a flag."""
    verified: list[VerifiedQuote] = []
    for q in quotes:
        text = (q.get("text") or "").strip()
        ts = (q.get("timestamp") or "").strip()
        if not text:
            continue
        ok = verify_quote(text, context_segments, ts or None)
        if ok:
            verified.append(VerifiedQuote(text=text, timestamp=ts, verified=True))
        else:
            verified.append(
                VerifiedQuote(
                    text=text,
                    timestamp=ts,
                    verified=False,
                    verification_note="Quote failed verification (not a verbatim substring of retrieved segments).",
                )
            )
    return verified
