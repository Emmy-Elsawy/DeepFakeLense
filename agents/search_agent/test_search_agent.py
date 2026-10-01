"""
test_search_agent.py — Standalone test suite for search_agent.py
=================================================================
Tests the search agent against mocked HTTP responses so no API keys
are required for CI.  Also includes a live integration path that
will be skipped unless keys are present.

Run with:
    pytest agents/search_agent/test_search_agent.py -v
or:
    python agents/search_agent/test_search_agent.py
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Allow running from project root
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import search_agent  # noqa: E402

MOCK_INPUT_PATH = os.path.join(_HERE, "mock_input.json")

# Preserve live keys from environment/.env before the test fixture clears them
_ORIGINAL_TAVILY_KEY = os.environ.get("TAVILY_API_KEY")
_ORIGINAL_GFC_KEY = os.environ.get("GOOGLE_FACTCHECK_API_KEY")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Ensure API keys are absent by default; individual tests can set them."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_FACTCHECK_API_KEY", raising=False)
    # Reload env-dependent module-level vars
    search_agent.TAVILY_API_KEY = None
    search_agent.GOOGLE_FACTCHECK_API_KEY = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_tavily_response(urls: list[str]) -> MagicMock:
    """Build a mock httpx response for the Tavily API."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [{"url": u, "title": "Result", "content": "..."} for u in urls]
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def _mock_gfc_response(urls: list[str]) -> MagicMock:
    """Build a mock httpx response for Google Fact Check Tools API."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "claims": [
            {"claimReview": [{"url": u, "publisher": {"name": "Snopes"}}]}
            for u in urls
        ]
    }
    mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# Output shape tests
# ---------------------------------------------------------------------------

class TestOutputShape:
    def test_returns_dict_with_candidate_urls_key(self):
        """Output must always be {"candidate_urls": [...]}."""
        with patch.object(search_agent, "_search_tavily", return_value=[]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=["https://reuters.com/a"]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("Some claim", "en")
        assert isinstance(result, dict)
        assert "candidate_urls" in result
        assert isinstance(result["candidate_urls"], list)

    def test_candidate_urls_capped_at_max(self):
        """Never return more than MAX_URLS URLs."""
        many_urls = [f"https://reuters.com/article-{i}" for i in range(20)]
        with patch.object(search_agent, "_search_tavily", return_value=many_urls):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("Claim text", "en")
        assert len(result["candidate_urls"]) <= search_agent.MAX_URLS

    def test_empty_claim_returns_empty_list(self):
        result = search_agent.run_search("", "en")
        assert result["candidate_urls"] == []

    def test_all_sources_empty_returns_empty(self):
        with patch.object(search_agent, "_search_tavily", return_value=[]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("Unknown claim", "en")
        assert result["candidate_urls"] == []


# ---------------------------------------------------------------------------
# Source priority / fallback tests
# ---------------------------------------------------------------------------

class TestSourcePriority:
    def test_tavily_used_when_available(self):
        """When Tavily returns results, DuckDuckGo should NOT be called."""
        tavily_url = "https://reuters.com/tavily-result"
        with patch.object(search_agent, "_search_tavily", return_value=[tavily_url]) as mock_t:
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]) as mock_ddg:
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("Claim", "en")

        mock_t.assert_called_once()
        mock_ddg.assert_not_called()
        assert tavily_url in result["candidate_urls"]

    def test_duckduckgo_fallback_when_tavily_empty(self):
        """When Tavily returns [], DuckDuckGo should be called."""
        ddg_url = "https://apnews.com/ddg-result"
        with patch.object(search_agent, "_search_tavily", return_value=[]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[ddg_url]) as mock_ddg:
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("Claim", "en")

        mock_ddg.assert_called_once()
        assert ddg_url in result["candidate_urls"]

    def test_google_factcheck_always_queried(self):
        """Google Fact Check should be queried regardless of Tavily/DDG results."""
        gfc_url = "https://snopes.com/gfc-result"
        with patch.object(search_agent, "_search_tavily", return_value=["https://reuters.com/1"]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[gfc_url]) as mock_gfc:
                    result = search_agent.run_search("Claim", "en")

        mock_gfc.assert_called_once()

    def test_trusted_domain_sorted_first(self):
        """Reuters/Snopes/WHO URLs should sort before unknown domains."""
        with patch.object(search_agent, "_search_tavily", return_value=[
            "https://randomsite.xyz/article",
            "https://reuters.com/trusted-article",
        ]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("Claim", "en")

        urls = result["candidate_urls"]
        assert urls[0] == "https://reuters.com/trusted-article"


# ---------------------------------------------------------------------------
# Deduplication tests
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_duplicate_urls_removed(self):
        duped = [
            "https://reuters.com/article",
            "https://reuters.com/article",
            "https://bbc.com/other",
        ]
        with patch.object(search_agent, "_search_tavily", return_value=duped):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("Claim", "en")

        assert len(result["candidate_urls"]) == len(set(result["candidate_urls"]))

    def test_urls_from_multiple_sources_deduped(self):
        shared_url = "https://snopes.com/shared"
        with patch.object(search_agent, "_search_tavily", return_value=[shared_url, "https://reuters.com/1"]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[shared_url]):
                    result = search_agent.run_search("Claim", "en")

        assert result["candidate_urls"].count(shared_url) == 1


# ---------------------------------------------------------------------------
# API key handling
# ---------------------------------------------------------------------------

class TestApiKeyHandling:
    def test_missing_tavily_key_falls_back_gracefully(self):
        """No TAVILY_API_KEY → should skip Tavily and fall through to DDG."""
        ddg_url = "https://bbc.com/ddg"
        with patch.object(search_agent, "_search_duckduckgo", return_value=[ddg_url]):
            with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                result = search_agent.run_search("Some claim", "en")
        assert ddg_url in result["candidate_urls"]

    def test_missing_gfc_key_does_not_crash(self):
        """No GOOGLE_FACTCHECK_API_KEY → GFC skipped, agent still returns results."""
        with patch.object(search_agent, "_search_tavily", return_value=["https://reuters.com/1"]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                result = search_agent.run_search("Some claim", "en")
        assert "candidate_urls" in result


# ---------------------------------------------------------------------------
# Language-specific tests
# ---------------------------------------------------------------------------

class TestLanguageHandling:
    def test_arabic_claim_builds_ar_query(self):
        """Arabic language should produce an Arabic query string with AR-specific trusted sites."""
        # Directly test the query builder — run_search delegates query building
        # to _build_query inside each source function, so we verify the function
        # directly rather than intercepting calls through mocked source functions.
        q = search_agent._build_query("علاج السرطان", "ar")
        assert "fatabyyano.net" in q or "misbar.com" in q, (
            f"Arabic query should reference Arabic fact-check sites, got: {q}"
        )

    def test_arabic_trusted_domains_in_output(self):
        """Arabic-specific trusted domains (Fatabyyano, Misbar) should rank highly."""
        ar_urls = [
            "https://randomnews.xyz/article",
            "https://fatabyyano.net/arabic-fact-check",
            "https://bbc.com/arabic/article",
        ]
        with patch.object(search_agent, "_search_tavily", return_value=ar_urls):
            with patch.object(search_agent, "_search_duckduckgo", return_value=[]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    result = search_agent.run_search("ادعاء عربي", "ar")

        urls = result["candidate_urls"]
        # fatabyyano should rank before randomnews.xyz
        if "https://fatabyyano.net/arabic-fact-check" in urls and "https://randomnews.xyz/article" in urls:
            fat_idx = urls.index("https://fatabyyano.net/arabic-fact-check")
            rnd_idx = urls.index("https://randomnews.xyz/article")
            assert fat_idx < rnd_idx


# ---------------------------------------------------------------------------
# Mock input JSON integration tests
# ---------------------------------------------------------------------------

class TestMockInputIntegration:
    @pytest.mark.skipif(not os.path.exists(MOCK_INPUT_PATH), reason="mock_input.json not found")
    def test_all_mock_cases_return_valid_shape(self):
        """Every test case in mock_input.json must produce valid output shape."""
        with open(MOCK_INPUT_PATH, encoding="utf-8") as f:
            mock_data = json.load(f)

        with patch.object(search_agent, "_search_tavily", return_value=[]):
            with patch.object(search_agent, "_search_duckduckgo", return_value=["https://reuters.com/mock"]):
                with patch.object(search_agent, "_search_google_factcheck", return_value=[]):
                    for tc in mock_data["test_cases"]:
                        result = search_agent.run_search(
                            claim=tc["input"]["claim"],
                            language=tc["input"]["language"],
                        )
                        assert "candidate_urls" in result, f"Missing key for case {tc['id']}"
                        assert isinstance(result["candidate_urls"], list), f"Not a list for case {tc['id']}"
                        assert len(result["candidate_urls"]) <= search_agent.MAX_URLS


# ---------------------------------------------------------------------------
# Internal helper unit tests
# ---------------------------------------------------------------------------

class TestInternalHelpers:
    def test_build_query_en_contains_fact_check_keywords(self):
        q = search_agent._build_query("COVID vaccine safety", "en")
        assert "fact check" in q.lower()
        assert "reuters.com" in q.lower()

    def test_build_query_ar_contains_arabic_keywords(self):
        q = search_agent._build_query("لقاح كوفيد", "ar")
        assert "fatabyyano.net" in q.lower() or "misbar.com" in q.lower()

    def test_dedupe_preserves_order(self):
        urls = ["https://a.com", "https://b.com", "https://a.com", "https://c.com"]
        result = search_agent._dedupe_urls(urls)
        assert result == ["https://a.com", "https://b.com", "https://c.com"]

    def test_domain_rank_reuters_is_low(self):
        """Reuters should have a lower (better) rank than an unknown domain."""
        reuters_rank = search_agent._domain_rank("https://reuters.com/article", "en")
        unknown_rank = search_agent._domain_rank("https://completelyrandom-xyz.net/post", "en")
        assert reuters_rank < unknown_rank

    def test_domain_rank_fatabyyano_low_for_ar(self):
        fat_rank = search_agent._domain_rank("https://fatabyyano.net/article", "ar")
        unknown_rank = search_agent._domain_rank("https://unknown-blog.io/post", "ar")
        assert fat_rank < unknown_rank


# ---------------------------------------------------------------------------
# Live integration tests (skipped unless API keys set)
# ---------------------------------------------------------------------------

class TestLiveIntegration:
    @pytest.mark.skipif(
        not _ORIGINAL_TAVILY_KEY,
        reason="TAVILY_API_KEY not set — skipping live test"
    )
    def test_live_tavily_english(self):
        search_agent.TAVILY_API_KEY = _ORIGINAL_TAVILY_KEY
        result = search_agent.run_search(
            "Did the COVID-19 vaccine get FDA full approval?", "en"
        )
        assert "candidate_urls" in result
        assert len(result["candidate_urls"]) > 0
        print(f"\n[LIVE] Tavily result: {result}")

    @pytest.mark.skipif(
        not _ORIGINAL_GFC_KEY,
        reason="GOOGLE_FACTCHECK_API_KEY not set — skipping live test"
    )
    def test_live_google_factcheck_english(self):
        search_agent.GOOGLE_FACTCHECK_API_KEY = _ORIGINAL_GFC_KEY
        result = search_agent._search_google_factcheck(
            "The moon landing was faked by NASA.", "en"
        )
        print(f"\n[LIVE] Google Fact Check URLs: {result}")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Manual runner
# ---------------------------------------------------------------------------

def _run_manual() -> None:
    """Quick smoke-test printed to stdout when run directly (no pytest)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\n=== Search Agent Manual Smoke Test ===\n")

    if not os.path.exists(MOCK_INPUT_PATH):
        print(f"[SKIP] mock_input.json not found at {MOCK_INPUT_PATH}")
        return

    with open(MOCK_INPUT_PATH, encoding="utf-8") as f:
        mock_data = json.load(f)

    for tc in mock_data["test_cases"]:
        print(f"--- Test case: {tc['id']} ---")
        print(f"Claim: {tc['input']['claim'][:80]}…")
        print(f"Lang:  {tc['input']['language']}")

        result = search_agent.run_search(
            claim=tc["input"]["claim"],
            language=tc["input"]["language"],
        )

        urls = result["candidate_urls"]
        print(f"Output candidate_urls ({len(urls)}):")
        for url in urls:
            print(f"  {url}")

        # Validate shape
        assert "candidate_urls" in result
        assert isinstance(urls, list)
        assert len(urls) <= search_agent.MAX_URLS
        print(f"[OK] Shape valid, ≤{search_agent.MAX_URLS} URLs\n")

    print("=== All manual search agent tests passed ===\n")


if __name__ == "__main__":
    _run_manual()
