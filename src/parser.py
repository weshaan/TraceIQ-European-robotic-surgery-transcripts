"""Parse expert-call transcripts into Segment objects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.step_log import log_step

TIMESTAMP_RE = re.compile(r"^\d{2}:\d{2}$")
SPEAKER_RE = re.compile(r"^(.+?):\s*(.*)$", re.DOTALL)
EXPERT_HEADER_RE = re.compile(r"^Expert\s+\d+\s+[–-]\s*(.+)$")
ROLE_RE = re.compile(r"^Role:\s*(.+)$")
MARKET_RE = re.compile(r"^Market:\s*(.+)$")


@dataclass
class Segment:
    segment_id: str
    expert_name: str
    expert_role: str
    market: str
    transcript_file: str
    timestamp: str
    timestamp_seconds: int
    speaker: str
    text: str


def timestamp_to_seconds(ts: str) -> int:
    minutes, seconds = ts.split(":")
    return int(minutes) * 60 + int(seconds)


def _market_slug(market: str, filename: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", market.lower()).strip("_")
    if slug:
        return slug
    stem = Path(filename).stem.lower()
    if "france" in stem:
        return "france"
    if "germany" in stem:
        return "germany"
    if "uk" in stem:
        return "uk"
    return "unknown"


def parse_transcript(path: Path | str) -> list[Segment]:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    lines = [line.rstrip("\r\n") for line in raw.splitlines()]

    expert_name = ""
    expert_role = ""
    market = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if m := EXPERT_HEADER_RE.match(line):
            expert_name = m.group(1).strip()
            i += 1
            continue
        if m := ROLE_RE.match(line):
            expert_role = m.group(1).strip()
            i += 1
            continue
        if m := MARKET_RE.match(line):
            market = m.group(1).strip()
            i += 1
            continue
        break

    if not expert_name or not market:
        raise ValueError(f"Missing header in {path.name}")

    slug = _market_slug(market, path.name)
    segments: list[Segment] = []
    while i < len(lines):
        ts_line = lines[i].strip()
        if not ts_line:
            i += 1
            continue
        if not TIMESTAMP_RE.match(ts_line):
            i += 1
            continue
        timestamp = ts_line
        i += 1
        if i >= len(lines):
            break
        turn = lines[i].strip()
        i += 1
        if not turn:
            continue
        m = SPEAKER_RE.match(turn)
        if not m:
            continue
        speaker, text = m.group(1).strip(), m.group(2).strip()
        ts_id = timestamp.replace(":", "_")
        segment_id = f"{slug}_{ts_id}"
        segments.append(
            Segment(
                segment_id=segment_id,
                expert_name=expert_name,
                expert_role=expert_role,
                market=market,
                transcript_file=path.name,
                timestamp=timestamp,
                timestamp_seconds=timestamp_to_seconds(timestamp),
                speaker=speaker,
                text=text,
            )
        )

    return segments


def load_all_transcripts(files_dir: Path | str) -> list[Segment]:
    with log_step("parse transcripts", detail=str(files_dir)):
        files_dir = Path(files_dir)
        paths = sorted(files_dir.glob("Transcript_*.txt"))
        if not paths:
            raise FileNotFoundError(f"No Transcript_*.txt in {files_dir}")
        all_segments: list[Segment] = []
        for p in paths:
            all_segments.extend(parse_transcript(p))
        return all_segments


def load_interview_questions(guide_path: Path | str) -> list[str]:
    with log_step("load interview guide", detail=str(guide_path)):
        guide_path = Path(guide_path)
        text = guide_path.read_text(encoding="utf-8")
        questions: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            m = re.match(r"^\d+\.\s+(.+)$", line)
            if m:
                questions.append(m.group(1).strip())
        if len(questions) < 6:
            raise ValueError(f"Expected 6 questions in {guide_path.name}, found {len(questions)}")
        return questions[:6]
