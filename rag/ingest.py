"""Clean, chunk, embed and index CI failure logs into Chroma (v0.2 flat RAG).

Pipeline: raw `gh run view --log-failed` text -> clean_log() -> chunk_log()
-> embedder -> Chroma collection (cosine). Each chunk carries its log_id,
repo and label as metadata so retrieval can aggregate chunks back to logs.

Build the persistent index used by retrieve.py:
    python -m rag.ingest --strategy tail
"""

import argparse
import csv
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "data" / "sample_logs"
INDEX_CSV = LOG_DIR / "index.csv"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION = "ci_failures"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

Embedder = Callable[[Sequence[str]], list[list[float]]]

# `gh --log-failed` lines look like "job\tstep\t2026-08-05T11:06:45.78Z text"
_PREFIX = re.compile(r"^[^\t]*\t[^\t]*\t")
_TIMESTAMP = re.compile(r"^﻿?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z ?")
# GitHub stores ESC either as the real byte or as the literal text "^["
_ANSI = re.compile(r"(?:\x1b|\^\[)\[[0-9;]*[A-Za-z]")
_GROUP_MARKER = re.compile(r"^##\[(end)?group\]")


@dataclass
class LogRecord:
    log_id: str
    repo: str
    label: str
    text: str


def clean_log(raw: str) -> str:
    """Strip gh's job/step prefix, timestamps, ANSI colours and group markers.

    Also drops each job's "Post job cleanup." section: it follows the real
    error, is near-identical across repos (git config resets, container
    removal), and would otherwise dominate the tail of most logs.
    """
    lines = []
    job, in_cleanup = None, False
    for line in raw.splitlines():
        line_job = line.split("\t", 1)[0] if "\t" in line else job
        if line_job != job:
            job, in_cleanup = line_job, False
        line = _PREFIX.sub("", line, count=1)
        line = _TIMESTAMP.sub("", line, count=1)
        line = _ANSI.sub("", line)
        line = _GROUP_MARKER.sub("", line).rstrip()
        if line == "Post job cleanup.":
            in_cleanup = True
        if line and not in_cleanup:
            lines.append(line)
    return "\n".join(lines)


def chunk_log(text: str, strategy: str, window: int = 15, overlap: int = 5) -> list[str]:
    """Split a cleaned log into the text units that get embedded.

    whole  - the full log as one chunk (the embedder truncates it, keeping
             only the start, which is mostly runner setup)
    tail   - only the last `window` lines, where failures usually surface
    window - fixed `window`-line windows overlapping by `overlap` lines
    """
    lines = text.splitlines()
    if not lines:
        return []
    if strategy == "whole":
        return [text]
    if strategy == "tail":
        return ["\n".join(lines[-window:])]
    if strategy == "window":
        step = max(window - overlap, 1)
        starts = range(0, max(len(lines) - overlap, 1), step)
        return ["\n".join(lines[s:s + window]) for s in starts]
    raise ValueError(f"unknown chunking strategy: {strategy!r}")


def sentence_transformer_embedder(model_name: str = DEFAULT_MODEL) -> Embedder:
    from sentence_transformers import SentenceTransformer  # heavy import, load lazily

    model = SentenceTransformer(model_name, device="cpu")

    def embed(texts: Sequence[str]) -> list[list[float]]:
        return model.encode(list(texts), normalize_embeddings=True, batch_size=32).tolist()

    return embed


def load_records(labelled_only: bool = False) -> list[LogRecord]:
    """Read data/sample_logs/index.csv and the log files it points to."""
    records = []
    with INDEX_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if labelled_only and not row["label"]:
                continue
            path = LOG_DIR / row["source"] / f"{row['log_id']}.log"
            raw = path.read_text(encoding="utf-8")
            records.append(LogRecord(row["log_id"], row["repo"], row["label"], clean_log(raw)))
    return records


def build_collection(
    client: chromadb.ClientAPI,
    records: Sequence[LogRecord],
    embed: Embedder,
    strategy: str,
    window: int = 15,
    overlap: int = 5,
    name: str = COLLECTION,
) -> chromadb.Collection:
    """(Re)create a collection holding every chunk of every record."""
    if name in [c.name for c in client.list_collections()]:
        client.delete_collection(name)
    collection = client.create_collection(name, metadata={"hnsw:space": "cosine"})

    ids, docs, metas = [], [], []
    for rec in records:
        for i, chunk in enumerate(chunk_log(rec.text, strategy, window, overlap)):
            ids.append(f"{rec.log_id}#{i}")
            docs.append(chunk)
            metas.append({"log_id": rec.log_id, "repo": rec.repo, "label": rec.label})

    batch = 256
    for s in range(0, len(ids), batch):
        collection.add(
            ids=ids[s:s + batch],
            documents=docs[s:s + batch],
            metadatas=metas[s:s + batch],
            embeddings=embed(docs[s:s + batch]),
        )
    return collection


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the persistent Chroma index.")
    parser.add_argument("--strategy", default="tail", choices=["whole", "tail", "window"])
    parser.add_argument("--window", type=int, default=15)
    parser.add_argument("--overlap", type=int, default=5)
    args = parser.parse_args()

    records = load_records()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = build_collection(
        client, records, sentence_transformer_embedder(),
        args.strategy, args.window, args.overlap,
    )
    print(f"indexed {len(records)} logs as {collection.count()} chunks -> {CHROMA_DIR}")


if __name__ == "__main__":
    main()
