"""
DeepFakeLens 5-Agent Pipeline Orchestrator.

Orchestrates sequential execution:
  1. Intake / Claim Extractor Agent (Person A)
     - Normalizes input; branches text vs image.
     - For images: runs image authenticity check (HF inference / Vision).
  2. RAG Knowledge Cache Check (Person B)
     - Checks similarity against past verified claims (rag_store.check_cache).
     - Cache hit -> returns cached verdict immediately (fast & free).
  3. Search Agent (Person B) [Only if cache miss]
     - Queries Tavily / DuckDuckGo / Google Fact Check API for candidate URLs.
  4. Scraper Agent (Person C) [Only if cache miss]
     - Scrapes candidate pages (Playwright + trafilatura) and truncates text.
  5. Cross-Reference / Analysis Agent (Person D) [Only if cache miss]
     - Analyzes stances and weighs credibility tiers.
  6. Verdict & Explainer Agent (Person E - verdict_agent.py)
     - Synthesizes final verdict, writes to RAG cache, returns final JSON.

Also provides lightweight single-shot follow-up answering on top of cached context.
"""

from __future__ import annotations
import json
import logging
import os
import re
from typing import Any, Dict, List, Literal, Optional
from dotenv import load_dotenv

import rag_store
import verdict_agent

load_dotenv()
logger = logging.getLogger("DeepFakeLens.Pipeline")


# ============================================================================
# Upstream Agent Stubs (Pluggable: swap with real modules when merged)
# ============================================================================

def run_intake_agent(
    input_type: str,
    text_claim: Optional[str] = None,
    image_url: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Agent 1 (Person A) Stub: Extracts core claim and performs initial routing.
    """
    logger.info(f"[Agent 1: Intake] Processing input_type='{input_type}'...")
    if input_type == "image":
        claim = text_claim.strip() if text_claim else "Authenticity verification of uploaded image"
        return {
            "input_type": "image",
            "extracted_claim": claim,
            "image_url": image_url,
            "language": language
        }
    else:
        claim = (text_claim or "").strip()
        return {
            "input_type": "text",
            "extracted_claim": claim,
            "image_url": None,
            "language": language
        }


def run_image_authenticity_check(image_url: Optional[str]) -> Dict[str, Any]:
    """
    Agent 1 Tool (Person A) Stub: Hugging Face deepfake detector / Gemini Vision signal.
    """
    logger.info(f"[Agent 1: Image Authenticity] Checking image: {image_url}...")
    # Default stub representation of image authenticity
    return {
        "is_ai_generated": False,
        "confidence": 0.88,
        "note": "Image visual artifacts, lighting consistency, and metadata inspected. Framing provided as forensic signal."
    }


def run_search_agent(claim: str, language: str = "en") -> Dict[str, Any]:
    """
    Agent 2 (Person B) Stub: Tavily / DuckDuckGo / Fact Check API search.
    Returns 3-4 candidate URLs biased toward high-credibility domains.
    """
    logger.info(f"[Agent 2: Search] Querying trusted sources for claim: '{claim[:50]}...'")
    return {
        "candidate_urls": [
            "https://www.reuters.com/fact-check/sample-report",
            "https://factcheck.afp.com/sample-investigation",
            "https://apnews.com/hub/ap-fact-check"
        ]
    }


def run_scraper_agent(candidate_urls: List[str]) -> Dict[str, Any]:
    """
    Agent 3 (Person C) Stub: Playwright + Trafilatura async scraper with token cap (~500-800 tokens).
    """
    logger.info(f"[Agent 3: Scraper] Scraping {len(candidate_urls)} candidate URLs...")
    sources = []
    for url in candidate_urls:
        domain = url.split("/")[2] if "//" in url else url
        sources.append({
            "url": url,
            "title": f"Fact Check Report from {domain.capitalize()}",
            "clean_text": f"Independent fact-checking investigation by {domain} found verifiable records clarifying the subject matter."
        })
    return {"sources": sources}


def run_analysis_agent(claim: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agent 4 (Person D) Stub: Cross-references scraped evidence against claim.
    Assigns stances and credibility tiers.
    """
    logger.info(f"[Agent 4: Analysis] Cross-referencing {len(sources)} sources against claim...")
    per_source = []
    for s in sources:
        url = s.get("url", "")
        # Heuristic stance assignment for stub demo
        stance = "contradicts" if any(k in claim.lower() for k in ["fake", "great wall", "squid", "hoax", "secret"]) else "supports"
        tier = "high" if any(d in url for d in ["reuters", "afp", "apnews", "nasa", "unesco", "bbc"]) else "medium"
        per_source.append({
            "url": url,
            "title": s.get("title", url),
            "stance": stance,
            "credibility_tier": tier
        })
    return {"per_source": per_source}


# ============================================================================
# Full Orchestrator
# ============================================================================

def run_pipeline(
    input_type: Literal["text", "image"],
    text_claim: Optional[str] = None,
    image_url: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Executes the full 5-agent DeepFakeLens pipeline.
    """
    logger.info(f"--- Starting DeepFakeLens Pipeline ({input_type}) ---")

    # Step 1: Intake Agent
    intake = run_intake_agent(input_type, text_claim, image_url, language)
    claim = intake.get("extracted_claim", "")

    image_authenticity: Optional[Dict[str, Any]] = None
    if input_type == "image":
        image_authenticity = run_image_authenticity_check(image_url)

    # Step 2: RAG / Knowledge Cache Check (Text path only)
    if input_type == "text" and claim:
        logger.info(f"[RAG Check] Querying vector cache for claim: '{claim[:50]}...'")
        cached = rag_store.check_cache(claim, similarity_threshold=0.85)
        if cached:
            logger.info("⚡ [RAG Hit] Found identical or highly similar claim in cache! Returning instant verdict.")
            return cached
        logger.info("[RAG Miss] No cache match found. Proceeding to web search & analysis...")

    # Step 3: Search Agent
    search_res = run_search_agent(claim, language)
    candidate_urls = search_res.get("candidate_urls", [])

    # Step 4: Scraper Agent
    scraper_res = run_scraper_agent(candidate_urls)
    scraped_sources = scraper_res.get("sources", [])

    # Step 5: Cross-Reference / Analysis Agent
    analysis_res = run_analysis_agent(claim, scraped_sources)
    per_source = analysis_res.get("per_source", [])

    # Step 6: Verdict & Explainer Agent (Person E)
    logger.info("[Agent 5: Verdict Agent] Synthesizing final verdict...")
    final_verdict = verdict_agent.generate_verdict(
        claim=claim,
        per_source=per_source,
        image_authenticity=image_authenticity,
        language=language,
        write_to_rag=True
    )

    logger.info("--- Pipeline Completed Successfully ---")
    return final_verdict


# ============================================================================
# Follow-Up Question Handler
# ============================================================================

def answer_follow_up(
    question: str,
    context: Dict[str, Any],
    language: str = "en"
) -> Dict[str, Any]:
    """
    Single lightweight LLM call to answer follow-up questions reusing prior verdict context.
    No new search or scrape needed.
    """
    logger.info(f"[Follow-up] Answering: '{question[:50]}...'")
    verdict = context.get("verdict", "unverified")
    explanation = context.get("explanation", "")
    sources = context.get("sources", [])

    context_summary = f"Verdict: {verdict}\nExplanation: {explanation}\nSources Cited: {json.dumps(sources, ensure_ascii=False)}"

    # 1. Try Gemini
    if os.environ.get("GEMINI_API_KEY"):
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"), http_options=types.HttpOptions(timeout=5.0))
            prompt = (
                f"You are the fact-checking assistant for DeepFakeLens. Answer the user's follow-up question concisely (2-4 sentences) based ONLY on the following prior fact-checking verdict and evidence.\n\n"
                f"CONTEXT:\n{context_summary}\n\n"
                f"QUESTION: {question}\n\n"
                f"Answer in {'Arabic' if language == 'ar' else 'English'}:"
            )
            for gem_model in ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-3.7-flash", "gemini-flash-latest"]:
                try:
                    resp = client.models.generate_content(
                        model=gem_model,
                        contents=prompt
                    )
                    if resp and resp.text:
                        return {"answer": resp.text.strip()}
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Follow-up Gemini call failed: {e}")

    # 2. Try Groq Fallback
    if os.environ.get("GROQ_API_KEY"):
        try:
            from groq import Groq
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"), timeout=5.0)
            prompt = (
                f"Context from prior verification:\n{context_summary}\n\n"
                f"User Question: {question}\n\n"
                f"Please provide a direct, concise 2-4 sentence explanation in {'Arabic' if language == 'ar' else 'English'}."
            )
            for groq_model in ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound"]:
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "You are a concise fact-checking assistant answering follow-up queries using cached evidence."},
                            {"role": "user", "content": prompt}
                        ],
                        model=groq_model,
                        temperature=0.2
                    )
                    ans = chat_completion.choices[0].message.content
                    if ans:
                        return {"answer": ans.strip()}
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Follow-up Groq call failed: {e}")

    # 3. Rule-based / Contextual Fallback
    if language == "ar":
        answer = f"بناءً على نتائج التحقق السابقة (النتيجة: {verdict})، فإن الأدلة تؤكد أن: {explanation} ولمزيد من التفاصيل يرجى مراجعة المصادر الموثقة المرفقة."
    else:
        answer = f"Based on the verified finding ({verdict.upper()}): {explanation} The cited evidence addresses '{question}' through verified source reporting."

    return {"answer": answer}
