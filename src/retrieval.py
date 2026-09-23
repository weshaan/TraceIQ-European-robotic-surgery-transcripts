"""Embedding index + top-k search (sentence-transformers + ChromaDB)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from src.parser import Segment
from src.step_log import log_step

if TYPE_CHECKING:
    pass

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_TOP_K = 6
# Cosine distance in Chroma: lower is more similar; threshold for "no relevant hits"
MAX_DISTANCE = 1.2


def segment_document(seg: Segment) -> str:
    return f"[{seg.timestamp}] {seg.speaker}: {seg.text}"


class TranscriptRetriever:
    """In-memory Chroma collection with local embedding model."""

    def __init__(
        self,
        segments: list[Segment],
        *,
        persist_dir: Path | str | None = None,
        embed_model_name: str = EMBED_MODEL,
    ):
        self.segments = segments
        self._by_id = {s.segment_id: s for s in segments}
        self._encode_lock = threading.Lock()
        with log_step("load embedding model", detail=embed_model_name):
            self.model = SentenceTransformer(embed_model_name)
        settings = Settings(anonymized_telemetry=False, allow_reset=True)
        with log_step("init chroma", detail=str(persist_dir or "memory")):
            if persist_dir:
                self.client = chromadb.PersistentClient(
                    path=str(persist_dir), settings=settings
                )
            else:
                self.client = chromadb.Client(settings)
            self.collection = self.client.get_or_create_collection(
                name="transcript_segments",
                metadata={"hnsw:space": "cosine"},
            )
        with log_step("index transcript segments", detail=f"{len(segments)} segments"):
            self._index_segments(segments)

    def _index_segments(self, segments: list[Segment]) -> None:
        if not segments:
            return
        try:
            if self.collection.count() >= len(segments):
                return
        except Exception:
            pass
        ids = [s.segment_id for s in segments]
        documents = [segment_document(s) for s in segments]
        with self._encode_lock:
            embeddings = self.model.encode(documents, show_progress_bar=False).tolist()
        metadatas = [
            {
                "expert_name": s.expert_name,
                "market": s.market,
                "timestamp": s.timestamp,
                "speaker": s.speaker,
                "transcript_file": s.transcript_file,
            }
            for s in segments
        ]
        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception:
            pass

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        expert_name: str | None = None,
        market: str | None = None,
    ) -> tuple[list[Segment], list[float]]:
        scope = expert_name or "all experts"
        if market:
            scope = f"{scope}, {market}"
        with log_step("vector search", detail=f"{scope!r} top_k={top_k}"):
            return self._search(query, top_k=top_k, expert_name=expert_name, market=market)

    def _search(
        self,
        query: str,
        *,
        top_k: int,
        expert_name: str | None,
        market: str | None,
    ) -> tuple[list[Segment], list[float]]:
        where: dict | None = None
        if expert_name and market:
            where = {
                "$and": [
                    {"expert_name": expert_name},
                    {"market": market},
                ]
            }
        elif expert_name:
            where = {"expert_name": expert_name}
        elif market:
            where = {"market": market}

        with self._encode_lock:
            q_emb = self.model.encode([query], show_progress_bar=False).tolist()
        kwargs: dict = {
            "query_embeddings": q_emb,
            "n_results": min(top_k, max(1, len(self.segments))),
        }
        if where:
            kwargs["where"] = where

        result = self.collection.query(**kwargs)
        ids = result["ids"][0] if result["ids"] else []
        distances = result["distances"][0] if result.get("distances") else []
        segs = [self._by_id[i] for i in ids if i in self._by_id]
        return segs, distances

    def has_relevant_hits(self, distances: list[float]) -> bool:
        if not distances:
            return False
        return distances[0] <= MAX_DISTANCE
