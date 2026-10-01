"""
search_agent.py — DeepFakeLens Search Agent
============================================
Only runs if the RAG cache (rag_store.check_cache) returned None.

Input  (from Intake Agent / mock):
    {"claim": str, "language": "en" | "ar"}

Output:
    {"candidate_urls": [str, ...]}   # 3–4 URLs, deduped, trusted-domain-first

Search strategy:
    1. Tavily Search API (TAVILY_API_KEY)       — primary
    2. duckduckgo-search (no key)               — fallback if Tavily errors / quota
    3. Google Fact Check Tools API              — supplemental structured fact-checks
       (GOOGLE_FACTCHECK_API_KEY)

All keys are read from environment variables; the agent degrades gracefully if
keys are missing (warns and skips that source).

Trusted domains (boosted to the top of results):
    Reuters, AFP, AAP, BBC, AP, Fatabyyano, Misbar, Snopes,
    relevant government / official health sources.
"""

from __future__ import annotations

import logging
import os
import time
import urllib.parse
from typing import Any

import httpx
from duckduckgo_search import DDGS
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file) or cwd
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TAVILY_API_KEY: str | None = os.environ.get("TAVILY_API_KEY")
GOOGLE_FACTCHECK_API_KEY: str | None = os.environ.get("GOOGLE_FACTCHECK_API_KEY")

MAX_URLS: int = 4  # hard cap on candidate_urls output
REQUEST_TIMEOUT: int = 15  # seconds

# Ordered from most trusted to least — used to sort/boost results
TRUSTED_DOMAINS: list[str] = [
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "afp.com",
    "aap.com.au",
    "fatabyyano.net",
    "misbar.com",
    "snopes.com",
    "factcheck.org",
    "politifact.com",
    "fullfact.org",
    "who.int",
    "cdc.gov",
    "fda.gov",
    "gov.au",
    "gov.uk",
    "aljazeera.com",
    "aljazeera.net",
    "france24.com",
    "dw.com",
    "theguardian.com",
    "washingtonpost.com",
    "nytimes.com",
    "scientificamerican.com",
]

# Arabic fact-checking / trusted domains (appended to the general list)
TRUSTED_DOMAINS_AR: list[str] = [
    "fatabyyano.net",
    "misbar.com",
    "aljazeera.net",
    "aljazeera.com",
    "france24.com",
    "bbc.com",
    "reuters.com",
    "who.int",
]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _domain_rank(url: str, language: str = "en") -> int:
    """
    Lower rank == more trusted.  Returns len(trusted_list) if not found
    (i.e. untrusted domains sort to the end).
    """
    domain_list = (
        TRUSTED_DOMAINS_AR + TRUSTED_DOMAINS
        if language == "ar"
        else TRUSTED_DOMAINS + TRUSTED_DOMAINS_AR
    )
    url_lower = url.lower()
    for i, domain in enumerate(domain_list):
        if domain in url_lower:
            return i
    return len(domain_list)


def _dedupe_urls(urls: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        normalised = url.strip().rstrip("/")
        if normalised not in seen:
            seen.add(normalised)
            out.append(normalised)
    return out


def _build_query(claim: str, language: str) -> str:
    """
    Build a search query biased toward fact-checking and trusted sources.
    For Arabic claims we prepend Arabic fact-check keywords.
    """
    if language == "ar":
        # Arabic: "fact check" prefix + trusted Arabic sites
        return (
            f'تحقق من صحة: "{claim}" '
            f'site:fatabyyano.net OR site:misbar.com OR site:aljazeera.net '
            f'OR site:bbc.com OR site:who.int OR site:reuters.com'
        )
    # English: standard fact-check prefix + trusted sites
    return (
        f'fact check: "{claim}" '
        f'site:reuters.com OR site:apnews.com OR site:snopes.com '
        f'OR site:factcheck.org OR site:bbc.com OR site:who.int '
        f'OR site:cdc.gov OR site:politifact.com OR site:fullfact.org'
    )


# ---------------------------------------------------------------------------
# Source 1 — Tavily
# ---------------------------------------------------------------------------


def _search_tavily(claim: str, language: str) -> list[str]:
    """
    Query Tavily Search API and return a list of result URLs.
    Returns [] on any error (including missing key, quota, network).
    """
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set — skipping Tavily search.")
        return []

    query = _build_query(claim, language)
    payload: dict[str, Any] = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": 8,
        "include_domains": TRUSTED_DOMAINS_AR if language == "ar" else TRUSTED_DOMAINS,
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                "https://api.tavily.com/search",
                json=payload,
            )
            response.raise_for_status()
            data: dict = response.json()

        urls: list[str] = [
            r["url"] for r in data.get("results", []) if r.get("url")
        ]
        logger.info("Tavily returned %d URLs.", len(urls))
        return urls

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (429, 402):
            logger.warning("Tavily quota exhausted (HTTP %d) — falling back.", exc.response.status_code)
        else:
            logger.error("Tavily HTTP error %d: %s", exc.response.status_code, exc)
        return []
    except Exception as exc:
        logger.error("Tavily search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Source 2 — DuckDuckGo (no-key fallback)
# ---------------------------------------------------------------------------


def _search_duckduckgo(claim: str, language: str) -> list[str]:
    """
    Query DuckDuckGo via duckduckgo-search and return result URLs.
    Returns [] on any error.
    """
    query = _build_query(claim, language)
    logger.info("Querying DuckDuckGo (fallback)…")

    try:
        results: list[dict] = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))

        urls: list[str] = [r["href"] for r in results if r.get("href")]
        logger.info("DuckDuckGo returned %d URLs.", len(urls))
        return urls

    except Exception as exc:
        logger.error("DuckDuckGo search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Source 3 — Google Fact Check Tools API
# ---------------------------------------------------------------------------


def _search_google_factcheck(claim: str, language: str) -> list[str]:
    """
    Query the Google Fact Check Tools API for structured fact-checks on the claim.
    Returns review article URLs (publisher URLs of the fact-check reviews).
    Returns [] on any error or missing key.
    """
    if not GOOGLE_FACTCHECK_API_KEY:
        logger.warning("GOOGLE_FACTCHECK_API_KEY not set — skipping Google Fact Check.")
        return []

    params: dict[str, str] = {
        "query": claim,
        "key": GOOGLE_FACTCHECK_API_KEY,
        "languageCode": language,
        "pageSize": "5",
    }
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data: dict = response.json()

        urls: list[str] = []
        for claim_item in data.get("claims", []):
            for review in claim_item.get("claimReview", []):
                article_url: str = review.get("url", "")
                if article_url:
                    urls.append(article_url)

        logger.info("Google Fact Check returned %d URLs.", len(urls))
        return urls

    except httpx.HTTPStatusError as exc:
        logger.error("Google Fact Check HTTP error %d: %s", exc.response.status_code, exc)
        return []
    except Exception as exc:
        logger.error("Google Fact Check search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_search(claim: str, language: str = "en") -> dict[str, list[str]]:
    """
    Main entry point for the Search Agent.

    Parameters
    ----------
    claim    : Normalised claim string from the Intake Agent.
    language : "en" or "ar".

    Returns
    -------
    {"candidate_urls": [str, ...]}   # max MAX_URLS entries
    """
    if not claim or not claim.strip():
        logger.error("run_search called with empty claim.")
        return {"candidate_urls": []}

    logger.info("Search agent starting. language=%s claim=%.100s", language, claim)
    all_urls: list[str] = []

    # --- Primary: Tavily ---
    tavily_urls = _search_tavily(claim, language)
    if tavily_urls:
        logger.info("Using Tavily results.")
        all_urls.extend(tavily_urls)
    else:
        # --- Fallback: DuckDuckGo ---
        logger.info("Tavily unavailable/empty — trying DuckDuckGo fallback.")
        ddg_urls = _search_duckduckgo(claim, language)
        all_urls.extend(ddg_urls)

    # --- Supplemental: Google Fact Check (always attempted) ---
    gfc_urls = _search_google_factcheck(claim, language)
    all_urls.extend(gfc_urls)

    # Dedupe and sort by trusted-domain rank
    unique_urls = _dedupe_urls(all_urls)
    ranked_urls = sorted(unique_urls, key=lambda u: _domain_rank(u, language))

    # Cap to MAX_URLS
    candidate_urls = ranked_urls[:MAX_URLS]

    logger.info(
        "Search agent done. %d candidates (from %d total).",
        len(candidate_urls),
        len(unique_urls),
    )
    return {"candidate_urls": candidate_urls}


# ---------------------------------------------------------------------------
# CLI / standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="DeepFakeLens Search Agent (standalone)")
    parser.add_argument("--claim", type=str, default="The COVID-19 vaccine contains microchips.")
    parser.add_argument("--language", type=str, default="en", choices=["en", "ar"])
    parser.add_argument("--mock-input", type=str, help="Path to mock_input.json; runs all test cases")
    args = parser.parse_args()

    if args.mock_input:
        with open(args.mock_input, encoding="utf-8") as f:
            mock = json.load(f)
        for tc in mock["test_cases"]:
            print(f"\n--- Test case: {tc['id']} ---")
            result = run_search(
                claim=tc["input"]["claim"],
                language=tc["input"]["language"],
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        result = run_search(claim=args.claim, language=args.language)
        print(json.dumps(result, ensure_ascii=False, indent=2))
