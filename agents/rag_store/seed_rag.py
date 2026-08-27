"""
seed_rag.py — One-time seed script for DeepFakeLens RAG cache
=============================================================
Reads seed_data.json, embeds each claim, and loads it into ChromaDB
via rag_store.write_to_cache().

Usage (run from project root or agents/rag_store/):
    python agents/rag_store/seed_rag.py

The script is idempotent: re-running it upserts existing records using
a deterministic UUID derived from the claim text, so no duplicates.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time

# Allow running from project root or from agents/rag_store/
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import rag_store  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SEED_FILE = os.path.join(_HERE, "seed_data.json")


def main() -> None:
    logger.info("=== DeepFakeLens RAG Seed Script ===")
    logger.info("Seed file: %s", SEED_FILE)

    if not os.path.exists(SEED_FILE):
        logger.error("Seed file not found: %s", SEED_FILE)
        sys.exit(1)

    with open(SEED_FILE, encoding="utf-8") as f:
        records: list[dict] = json.load(f)

    logger.info("Loaded %d records from seed file.", len(records))

    # Boot the store (loads model + opens DB)
    rag_store.init_store()

    start = time.perf_counter()
    ok = 0
    err = 0

    for i, record in enumerate(records, 1):
        claim: str = record.get("claim", "").strip()
        if not claim:
            logger.warning("Record %d has an empty claim — skipping.", i)
            err += 1
            continue

        verdict_json: dict = {
            "claim": claim,
            "verdict": record.get("verdict", "unverified"),
            "explanation": record.get("explanation", ""),
            "sources": record.get("sources", []),
        }

        try:
            rag_store.write_to_cache(claim, verdict_json)
            ok += 1
        except Exception as exc:
            logger.error("Failed to write record %d: %s", i, exc)
            err += 1

    elapsed = time.perf_counter() - start
    logger.info(
        "Seeding complete. %d written, %d errors. Elapsed: %.2fs.",
        ok,
        err,
        elapsed,
    )

    # Verify final count
    rag_store._ensure_init()
    count = rag_store._collection.count()  # type: ignore[union-attr]
    logger.info("ChromaDB collection now contains %d documents.", count)


if __name__ == "__main__":
    main()
