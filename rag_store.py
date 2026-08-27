"""
RAG Store & Knowledge Cache Interface for DeepFakeLens.

Owned by Person B (Search Agent + RAG Knowledge Cache).
Provides:
  - init_store(): Initializes vector collection / local cache.
  - check_cache(claim_text): Checks similarity against past verified claims (threshold > 0.85).
  - write_to_cache(claim_text, verdict_json): Saves verified claim & verdict into cache.
"""

from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Optional

# In-memory storage for cached claims when running without full ChromaDB setup
_IN_MEMORY_CACHE: List[Dict[str, Any]] = [
    {
        "claim": "NASA confirmed the Great Wall of China is visible from the Moon.",
        "verdict": {
            "verdict": "false",
            "confidence": 0.98,
            "explanation": "NASA astronauts and optical physics have repeatedly confirmed that the Great Wall of China is not visible from low Earth orbit without magnification, and impossible to see from the Moon with the naked eye.",
            "sources": [
                {
                    "title": "NASA - China's Wall Less Great in View from Space",
                    "url": "https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
                    "stance": "contradicts"
                }
            ],
            "image_authenticity": None
        }
    }
]

_CHROMA_INITIALIZED = False
_CHROMA_COLLECTION = None


def _tokenize(text: str) -> List[str]:
    """Tokenize and normalize text for similarity computation."""
    return re.findall(r"\w+", text.lower())


def _cosine_similarity_sparse(text1: str, text2: str) -> float:
    """
    Lightweight local text cosine similarity fallback.
    Used when sentence-transformers is not initialized in the current process.
    """
    tokens1 = _tokenize(text1)
    tokens2 = _tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0

    vec1: Dict[str, int] = {}
    for t in tokens1:
        vec1[t] = vec1.get(t, 0) + 1

    vec2: Dict[str, int] = {}
    for t in tokens2:
        vec2[t] = vec2.get(t, 0) + 1

    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([val**2 for val in vec1.values()])
    sum2 = sum([val**2 for val in vec2.values()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return float(numerator) / denominator


def init_store(persist_directory: Optional[str] = "./chroma_db") -> None:
    """
    Initializes ChromaDB collection or in-memory fallback.
    """
    global _CHROMA_INITIALIZED, _CHROMA_COLLECTION
    try:
        import chromadb
        client = chromadb.PersistentClient(path=persist_directory)
        _CHROMA_COLLECTION = client.get_or_create_collection(name="fact_checks")
        _CHROMA_INITIALIZED = True
    except Exception:
        # Fallback to robust in-memory cache
        _CHROMA_INITIALIZED = False
        _CHROMA_COLLECTION = None


def check_cache(claim_text: str, similarity_threshold: float = 0.85) -> Optional[Dict[str, Any]]:
    """
    Query knowledge store for previously verified claim.
    Returns the cached verdict JSON if similarity > threshold, otherwise None.
    """
    if not claim_text or not claim_text.strip():
        return None

    # 1. If ChromaDB is initialized, attempt vector query
    if _CHROMA_INITIALIZED and _CHROMA_COLLECTION is not None:
        try:
            results = _CHROMA_COLLECTION.query(
                query_texts=[claim_text],
                n_results=1
            )
            if results and results.get("distances") and len(results["distances"][0]) > 0:
                distance = results["distances"][0][0]
                # Cosine distance to similarity conversion: sim = 1 - distance
                similarity = 1.0 - distance
                if similarity >= similarity_threshold:
                    import json
                    metadata = results["metadatas"][0][0]
                    return json.loads(metadata.get("verdict_json", "{}"))
        except Exception:
            pass

    # 2. In-memory similarity fallback
    best_match = None
    highest_sim = 0.0

    for item in _IN_MEMORY_CACHE:
        sim = _cosine_similarity_sparse(claim_text, item["claim"])
        if sim > highest_sim:
            highest_sim = sim
            best_match = item["verdict"]

    if highest_sim >= similarity_threshold:
        return best_match

    return None


def write_to_cache(claim_text: str, verdict_json: Dict[str, Any]) -> None:
    """
    Saves a newly verified claim and its final verdict into the cache.
    """
    if not claim_text or not verdict_json:
        return

    # 1. Update in-memory cache
    _IN_MEMORY_CACHE.append({
        "claim": claim_text,
        "verdict": verdict_json
    })

    # 2. Update ChromaDB if initialized
    if _CHROMA_INITIALIZED and _CHROMA_COLLECTION is not None:
        try:
            import json
            import uuid
            doc_id = str(uuid.uuid4())
            _CHROMA_COLLECTION.add(
                documents=[claim_text],
                metadatas=[{"verdict_json": json.dumps(verdict_json)}],
                ids=[doc_id]
            )
        except Exception:
            pass
