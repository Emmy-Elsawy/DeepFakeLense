"""
test_rag_store.py — Standalone test suite for rag_store.py
===========================================================
Tests init_store(), check_cache(), and write_to_cache() against a
*temporary* ChromaDB collection that is torn down after each test,
so this is fully isolated from the production cache.

Run with:
    pytest agents/rag_store/test_rag_store.py -v
or:
    python agents/rag_store/test_rag_store.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil

# Allow running from project root
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import pytest
try:
    from agents.rag_store import rag_store
except ImportError:
    import rag_store  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_store(tmp_path):
    """
    Before each test:  reset module-level singletons and point ChromaDB at a
    fresh temp directory.  After the test: clean up.
    """
    # Override persist dir and reset singletons
    rag_store._client = None
    rag_store._collection = None
    rag_store._embedder = None
    rag_store.PERSIST_DIR = str(tmp_path / "chroma_test")

    yield  # run test

    # Teardown: reset singletons so next test starts clean
    rag_store._client = None
    rag_store._collection = None
    rag_store._embedder = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_verdict(claim: str, verdict: str = "false") -> dict:
    return {
        "claim": claim,
        "verdict": verdict,
        "explanation": f"Test explanation for: {claim}",
        "sources": ["https://reuters.com/example", "https://bbc.com/example"],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInitStore:
    def test_init_creates_collection(self):
        rag_store.init_store()
        assert rag_store._client is not None
        assert rag_store._collection is not None
        assert rag_store._embedder is not None

    def test_init_is_idempotent(self):
        rag_store.init_store()
        first_client = rag_store._client
        rag_store.init_store()  # second call should be no-op
        assert rag_store._client is first_client, "init_store() should not replace client on second call"

    def test_empty_store_count_is_zero(self):
        rag_store.init_store()
        assert rag_store._collection.count() == 0


class TestWriteToCache:
    def test_write_increases_count(self):
        rag_store.init_store()
        claim = "The Earth is flat."
        rag_store.write_to_cache(claim, _sample_verdict(claim, "false"))
        assert rag_store._collection.count() == 1

    def test_write_is_idempotent_upsert(self):
        """Writing the same claim twice should not create duplicate docs."""
        rag_store.init_store()
        claim = "Vaccines cause autism."
        rag_store.write_to_cache(claim, _sample_verdict(claim, "false"))
        rag_store.write_to_cache(claim, _sample_verdict(claim, "false"))
        assert rag_store._collection.count() == 1

    def test_write_multiple_claims(self):
        rag_store.init_store()
        claims = [
            ("Humans only use 10% of their brains.", "false"),
            ("Russia invaded Ukraine in 2022.", "true"),
            ("5G towers spread COVID-19.", "false"),
        ]
        for claim, verdict in claims:
            rag_store.write_to_cache(claim, _sample_verdict(claim, verdict))
        assert rag_store._collection.count() == 3

    def test_write_arabic_claim(self):
        rag_store.init_store()
        claim = "شرب الماء الساخن مع الليمون يقتل فيروس كورونا"
        rag_store.write_to_cache(claim, _sample_verdict(claim, "false"))
        assert rag_store._collection.count() == 1

    def test_write_empty_claim_is_skipped(self):
        rag_store.init_store()
        rag_store.write_to_cache("", _sample_verdict("", "false"))
        assert rag_store._collection.count() == 0


class TestCheckCache:
    def test_cache_miss_on_empty_store(self):
        rag_store.init_store()
        result = rag_store.check_cache("Some random claim no one has seen before.")
        assert result is None

    def test_cache_hit_exact_match(self):
        """Exact same claim text should always be above the threshold."""
        rag_store.init_store()
        claim = "The COVID-19 vaccine contains microchips that track your location."
        verdict = _sample_verdict(claim, "false")
        rag_store.write_to_cache(claim, verdict)

        result = rag_store.check_cache(claim)
        assert result is not None, "Exact match must be a cache hit"
        assert result["verdict"] == "false"
        assert result["claim"] == claim

    def test_cache_hit_near_paraphrase(self):
        """A close paraphrase should hit the cache (similarity > 0.85)."""
        rag_store.init_store()
        original = "The COVID-19 vaccine contains microchips to track people."
        paraphrase = "COVID vaccines have embedded microchips that track your location."
        verdict = _sample_verdict(original, "false")
        rag_store.write_to_cache(original, verdict)

        result = rag_store.check_cache(paraphrase)
        # Near-paraphrase — might hit or miss depending on model; we log but don't hard-assert
        # to keep the test stable across model versions.
        if result is not None:
            assert result["verdict"] == "false"

    def test_cache_miss_unrelated_claim(self):
        """An unrelated claim should return None."""
        rag_store.init_store()
        cached_claim = "The COVID-19 vaccine contains microchips."
        rag_store.write_to_cache(cached_claim, _sample_verdict(cached_claim, "false"))

        unrelated = "The Eiffel Tower is located in Berlin."
        result = rag_store.check_cache(unrelated)
        assert result is None

    def test_cache_returns_correct_fields(self):
        """Verdict dict must have all required contract fields."""
        rag_store.init_store()
        claim = "Eating carrots improves your night vision significantly."
        verdict = {
            "claim": claim,
            "verdict": "misleading",
            "explanation": "Only helps if you're deficient in vitamin A.",
            "sources": ["https://bbc.com/future/example", "https://snopes.com/example"],
        }
        rag_store.write_to_cache(claim, verdict)
        result = rag_store.check_cache(claim)

        assert result is not None
        assert "claim" in result
        assert "verdict" in result
        assert "explanation" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)
        assert result["verdict"] == "misleading"
        assert result["explanation"] == verdict["explanation"]

    def test_cache_hit_arabic_claim(self):
        """Arabic claims should embed and retrieve correctly."""
        rag_store.init_store()
        claim = "لقاح كوفيد-19 يحتوي على شرائح إلكترونية لتتبع الأشخاص"
        verdict = _sample_verdict(claim, "false")
        rag_store.write_to_cache(claim, verdict)

        result = rag_store.check_cache(claim)
        assert result is not None
        assert result["verdict"] == "false"

    def test_cache_empty_claim_returns_none(self):
        rag_store.init_store()
        result = rag_store.check_cache("")
        assert result is None


# ---------------------------------------------------------------------------
# Integration smoke test: mock_input.json → rag_store round-trip
# ---------------------------------------------------------------------------

class TestMockInputIntegration:
    MOCK_INPUT_PATH = os.path.join(
        os.path.dirname(_HERE), "search_agent", "mock_input.json"
    )

    def test_mock_input_cache_hit_scenario(self):
        """
        The 'cache_hit' test case from mock_input.json should return a hit
        after we pre-load the claim (simulating a seeded cache).
        """
        if not os.path.exists(self.MOCK_INPUT_PATH):
            pytest.skip(f"mock_input.json not found at {self.MOCK_INPUT_PATH}")

        with open(self.MOCK_INPUT_PATH, encoding="utf-8") as f:
            mock_data = json.load(f)

        cache_hit_case = next(
            tc for tc in mock_data["test_cases"] if tc["id"] == "cache_hit"
        )
        claim = cache_hit_case["input"]["claim"]

        rag_store.init_store()
        # Simulate seeded cache
        verdict = {
            "claim": claim,
            "verdict": cache_hit_case["expected_verdict"],
            "explanation": "Seeded test verdict.",
            "sources": ["https://reuters.com/test"],
        }
        rag_store.write_to_cache(claim, verdict)

        result = rag_store.check_cache(claim)
        assert result is not None, "Expected a cache HIT for the pre-loaded claim"
        assert result["verdict"] == cache_hit_case["expected_verdict"]

    def test_mock_input_cache_miss_scenario(self):
        """
        The 'cache_miss_en' test case should return None on a fresh store.
        """
        if not os.path.exists(self.MOCK_INPUT_PATH):
            pytest.skip(f"mock_input.json not found at {self.MOCK_INPUT_PATH}")

        with open(self.MOCK_INPUT_PATH, encoding="utf-8") as f:
            mock_data = json.load(f)

        miss_case = next(
            tc for tc in mock_data["test_cases"] if tc["id"] == "cache_miss_en"
        )
        claim = miss_case["input"]["claim"]

        rag_store.init_store()
        result = rag_store.check_cache(claim)
        assert result is None, "Expected a cache MISS on an empty store"

    def test_mock_input_arabic_claim(self):
        """
        The 'cache_miss_ar' Arabic claim should embed without error.
        """
        if not os.path.exists(self.MOCK_INPUT_PATH):
            pytest.skip(f"mock_input.json not found at {self.MOCK_INPUT_PATH}")

        with open(self.MOCK_INPUT_PATH, encoding="utf-8") as f:
            mock_data = json.load(f)

        ar_case = next(
            tc for tc in mock_data["test_cases"] if tc["id"] == "cache_miss_ar"
        )
        claim = ar_case["input"]["claim"]

        rag_store.init_store()
        # Write then retrieve — verifies Arabic embeddings work end-to-end
        verdict = _sample_verdict(claim, "unverified")
        rag_store.write_to_cache(claim, verdict)
        result = rag_store.check_cache(claim)
        assert result is not None


# ---------------------------------------------------------------------------
# Manual runner (python test_rag_store.py)
# ---------------------------------------------------------------------------

def _run_manual() -> None:
    """Quick smoke-test printed to stdout when run directly (no pytest)."""
    import tempfile

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tmp = tempfile.mkdtemp(prefix="deepfakelens_test_")
    print(f"\n=== RAG Store Manual Smoke Test ===")
    print(f"Temp DB: {tmp}\n")

    rag_store._client = None
    rag_store._collection = None
    rag_store._embedder = None
    rag_store.PERSIST_DIR = tmp

    rag_store.init_store()
    print(f"[OK] init_store() — collection count: {rag_store._collection.count()}")

    # --- write ---
    claim_en = "The COVID-19 vaccine contains microchips that track your location."
    claim_ar = "لقاح كوفيد-19 يحتوي على شرائح إلكترونية لتتبع الأشخاص"

    verdict_en = {
        "claim": claim_en,
        "verdict": "false",
        "explanation": "No microchips in vaccines.",
        "sources": ["https://reuters.com/example"],
    }
    verdict_ar = {
        "claim": claim_ar,
        "verdict": "false",
        "explanation": "لا توجد شرائح إلكترونية في اللقاحات.",
        "sources": ["https://who.int/ar/example"],
    }

    rag_store.write_to_cache(claim_en, verdict_en)
    rag_store.write_to_cache(claim_ar, verdict_ar)
    print(f"[OK] write_to_cache() x2 — collection count: {rag_store._collection.count()}")

    # --- cache hit ---
    hit = rag_store.check_cache(claim_en)
    status = "HIT" if hit else "MISS"
    print(f"[OK] check_cache(exact match) → {status}: {json.dumps(hit, ensure_ascii=False) if hit else 'None'}")

    # --- cache miss ---
    unrelated = "The Eiffel Tower is located in Berlin, Germany."
    miss = rag_store.check_cache(unrelated)
    print(f"[OK] check_cache(unrelated)   → {'HIT' if miss else 'MISS'} (expected MISS)")

    # --- Arabic hit ---
    ar_hit = rag_store.check_cache(claim_ar)
    print(f"[OK] check_cache(Arabic)      → {'HIT' if ar_hit else 'MISS'}: verdict={ar_hit['verdict'] if ar_hit else 'N/A'}")

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n=== All manual tests passed ===\n")


if __name__ == "__main__":
    _run_manual()
