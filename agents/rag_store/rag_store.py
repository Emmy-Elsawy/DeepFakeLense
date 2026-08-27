"""
rag_store.py — DeepFakeLens RAG Cache
======================================
Provides a persistent ChromaDB-backed semantic cache for verified fact-check
verdicts. Embeddings are computed locally via sentence-transformers so there
are zero external API calls at inference time.

Public API
----------
    init_store()  -> None
    check_cache(claim_text: str) -> dict | None
    write_to_cache(claim_text: str, verdict_json: dict) -> None

Verdict JSON shape (matches Final Pipeline Output contract):
    {
        "claim":       str,
        "verdict":     "true" | "false" | "misleading" | "unverified",
        "explanation": str,
        "sources":     list[str]
    }
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME: str = "factcheck_cache"
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD: float = 0.85  # cosine similarity; 1.0 == identical

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons (loaded once at startup / first call)
# ---------------------------------------------------------------------------

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_embedder: SentenceTransformer | None = None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def init_store() -> None:
    """
    Initialise (or reload) the ChromaDB persistent client and the
    sentence-transformer embedder.  Safe to call multiple times — will
    short-circuit if already initialised.
    """
    global _client, _collection, _embedder

    if _client is not None:
        logger.debug("RAG store already initialised — skipping.")
        return

    logger.info("Loading embedding model '%s' …", EMBEDDING_MODEL)
    _embedder = SentenceTransformer(EMBEDDING_MODEL)
    logger.info("Embedding model loaded.")

    logger.info("Opening ChromaDB at '%s' …", PERSIST_DIR)
    _client = chromadb.PersistentClient(
        path=PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        # ChromaDB's built-in cosine similarity
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(
        "RAG store ready. Collection '%s' has %d documents.",
        COLLECTION_NAME,
        _collection.count(),
    )


def _ensure_init() -> None:
    """Raise if init_store() has not been called yet."""
    if _collection is None or _embedder is None:
        raise RuntimeError(
            "RAG store is not initialised. Call init_store() first."
        )


def _embed(text: str) -> list[float]:
    """Return a normalised embedding vector for *text*."""
    _ensure_init()
    vector = _embedder.encode(text, normalize_embeddings=True)  # type: ignore[union-attr]
    return vector.tolist()


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


def check_cache(claim_text: str) -> dict[str, Any] | None:
    """
    Embed *claim_text* and query the store for the nearest neighbour.

    Returns the stored verdict dict if cosine similarity > SIMILARITY_THRESHOLD,
    otherwise returns None (cache miss).

    ChromaDB returns distances in [0, 2] for cosine space where
    distance = 1 - cosine_similarity.  We convert:
        similarity = 1 - distance
    """
    _ensure_init()

    if not claim_text or not claim_text.strip():
        logger.warning("check_cache called with empty claim — returning None.")
        return None

    query_embedding = _embed(claim_text)

    results = _collection.query(  # type: ignore[union-attr]
        query_embeddings=[query_embedding],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    # If the collection is empty ChromaDB still returns lists with one item
    distances: list[float] = results.get("distances", [[]])[0]
    documents: list[str] = results.get("documents", [[]])[0]
    metadatas: list[dict] = results.get("metadatas", [[]])[0]

    if not distances:
        logger.info("Cache MISS (empty store) for: %.80s", claim_text)
        return None

    distance: float = distances[0]
    similarity: float = 1.0 - distance

    logger.info(
        "Cache query — similarity=%.4f (threshold=%.2f) for: %.80s",
        similarity,
        SIMILARITY_THRESHOLD,
        claim_text,
    )

    if similarity >= SIMILARITY_THRESHOLD:
        # Reconstruct the full verdict JSON from stored metadata + document
        metadata: dict = metadatas[0]
        verdict_json: dict = {
            "claim": documents[0],
            "verdict": metadata.get("verdict", "unverified"),
            "explanation": metadata.get("explanation", ""),
            "sources": json.loads(metadata.get("sources_json", "[]")),
        }
        logger.info("Cache HIT  — verdict=%s", verdict_json["verdict"])
        return verdict_json

    logger.info("Cache MISS — similarity too low (%.4f < %.2f).", similarity, SIMILARITY_THRESHOLD)
    return None


def write_to_cache(claim_text: str, verdict_json: dict[str, Any]) -> None:
    """
    Embed *claim_text* and upsert the claim + verdict into ChromaDB.

    ChromaDB metadata values must be str / int / float — we JSON-serialise
    the ``sources`` list and store it as ``sources_json``.
    """
    _ensure_init()

    if not claim_text or not claim_text.strip():
        logger.warning("write_to_cache called with empty claim — skipping.")
        return

    embedding = _embed(claim_text)
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, claim_text))

    metadata: dict[str, str] = {
        "verdict": str(verdict_json.get("verdict", "unverified")),
        "explanation": str(verdict_json.get("explanation", "")),
        # ChromaDB doesn't support list metadata; serialise sources
        "sources_json": json.dumps(verdict_json.get("sources", [])),
    }

    _collection.upsert(  # type: ignore[union-attr]
        ids=[doc_id],
        embeddings=[embedding],
        documents=[claim_text],
        metadatas=[metadata],
    )
    logger.info(
        "Wrote to cache — id=%s verdict=%s claim=%.80s",
        doc_id,
        metadata["verdict"],
        claim_text,
    )
