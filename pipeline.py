"""
DeepFakeLens 5-Agent Pipeline Orchestrator.
Wires together the real implementations of all 5 agents:
  1. Intake / Claim Extractor Agent (Person A — intake_agent.py)
  2. RAG Knowledge Cache Check (Person B — agents/rag_store/rag_store.py)
  3. Search Agent (Person B — agents/search_agent/search_agent.py)
  4. Scraper Agent (Person C — scraper_agent/scraper_agent.py)
  5. Cross-Reference / Analysis Agent (Person D — agent-analysis/analysis_agent.py)
  6. Verdict & Explainer Agent (Person E — verdict_agent.py)
"""

from __future__ import annotations
import json
import logging
import os
import sys
from typing import Any, Dict, List, Literal, Optional
from dotenv import load_dotenv

# Ensure subdirectories are accessible on sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ANALYSIS_DIR = os.path.join(_HERE, "agent-analysis")
_AGENTS_DIR = os.path.join(_HERE, "agents")
_SEARCH_DIR = os.path.join(_AGENTS_DIR, "search_agent")
_RAG_DIR = os.path.join(_AGENTS_DIR, "rag_store")
_SCRAPER_DIR = os.path.join(_HERE, "scraper_agent")

for p in [_HERE, _ANALYSIS_DIR, _AGENTS_DIR, _SEARCH_DIR, _RAG_DIR, _SCRAPER_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

load_dotenv()
logger = logging.getLogger("DeepFakeLens.Pipeline")

# Import real agent implementations
import intake_agent
import rag_store
try:
    from agents.search_agent import run_search
except ImportError:
    from search_agent import run_search

try:
    from scraper_agent import run_scraper
except ImportError:
    from scraper_agent.scraper_agent import run_scraper

try:
    from analysis_agent import run_analysis
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("analysis_agent", os.path.join(_ANALYSIS_DIR, "analysis_agent.py"))
    analysis_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analysis_mod)
    run_analysis = analysis_mod.run_analysis

import verdict_agent


# ============================================================================
# Full 5-Agent Sequential Pipeline
# ============================================================================

def run_pipeline(
    input_type: Literal["text", "image"],
    text_claim: Optional[str] = None,
    image_url: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Executes the full 5-agent DeepFakeLens pipeline sequentially:
      Intake → RAG Check (skip to cached verdict if hit) → Search → Scraper → Analysis → Verdict
    """
    logger.info(f"=== [DeepFakeLens] Starting Pipeline Execution (input_type='{input_type}', lang='{language}') ===")

    # ------------------------------------------------------------------------
    # STEP 1: Intake / Claim Extractor Agent (Person A)
    # ------------------------------------------------------------------------
    logger.info("[Step 1: Intake Agent] Running claim extraction and routing...")
    intake_result = intake_agent.run_intake(
        input_type=input_type,
        text_claim=text_claim,
        image_url=image_url,
        language=language
    )

    # If input is image, intake_agent executes deepfake detection & vision and derives verdict
    if input_type == "image":
        logger.info("[Step 1: Intake Agent] Image path completed. Returning image verdict directly.")
        # Ensure confidence is normalized float 0.0 - 1.0
        conf = float(intake_result.get("confidence", 0.90))
        if conf > 1.0:
            conf = conf / 100.0
        intake_result["confidence"] = round(conf, 2)
        return intake_result

    # Text claim extraction
    claim = intake_result.get("extracted_claim", (text_claim or "").strip())
    detected_lang = intake_result.get("language", language)
    logger.info(f"[Step 1: Intake Agent] Extracted claim: '{claim}' (language='{detected_lang}')")

    # ------------------------------------------------------------------------
    # STEP 2: RAG Knowledge Cache Check (Person B)
    # ------------------------------------------------------------------------
    logger.info(f"[Step 2: RAG Cache] Querying ChromaDB cache for claim: '{claim[:60]}...'")
    cached_verdict = rag_store.check_cache(claim, similarity_threshold=0.85)
    if cached_verdict:
        logger.info(f"⚡ [Step 2: RAG Cache HIT] Found pre-verified verdict in RAG cache! Verdict: {cached_verdict.get('verdict')}")
        
        # Normalize cached sources to match List[SourceItem] contract
        raw_sources = cached_verdict.get("sources", [])
        normalized_sources = []
        for s in raw_sources:
            if isinstance(s, str):
                domain = s.split("/")[2] if "//" in s else s
                v = cached_verdict.get("verdict", "unverified")
                stance = "contradicts" if v == "false" else ("supports" if v == "true" else "context")
                normalized_sources.append({
                    "title": f"Verified Source ({domain})",
                    "url": s,
                    "stance": stance
                })
            elif isinstance(s, dict):
                normalized_sources.append({
                    "title": s.get("title", s.get("url", "")),
                    "url": s.get("url", ""),
                    "stance": s.get("stance", "context")
                })
        cached_verdict["sources"] = normalized_sources
        
        if "confidence" not in cached_verdict:
            cached_verdict["confidence"] = 0.95
        if "image_authenticity" not in cached_verdict:
            cached_verdict["image_authenticity"] = None
            
        return cached_verdict

    logger.info("[Step 2: RAG Cache MISS] No semantic match in cache. Proceeding to web search...")

    # ------------------------------------------------------------------------
    # STEP 3: Search Agent (Person B)
    # ------------------------------------------------------------------------
    logger.info(f"[Step 3: Search Agent] Searching web sources for claim: '{claim[:60]}...'")
    search_output = run_search(claim=claim, language=detected_lang)
    candidate_urls = search_output.get("candidate_urls", [])
    logger.info(f"[Step 3: Search Agent] Retrieved {len(candidate_urls)} candidate URLs: {candidate_urls}")

    # ------------------------------------------------------------------------
    # STEP 4: Scraper Agent (Person C)
    # ------------------------------------------------------------------------
    logger.info(f"[Step 4: Scraper Agent] Scraping {len(candidate_urls)} candidate pages...")
    scraper_output = run_scraper({"candidate_urls": candidate_urls})
    scraped_sources = scraper_output.get("sources", [])
    logger.info(f"[Step 4: Scraper Agent] Successfully scraped {len(scraped_sources)} sources with clean text.")

    # ------------------------------------------------------------------------
    # STEP 5: Cross-Reference / Analysis Agent (Person D)
    # ------------------------------------------------------------------------
    logger.info(f"[Step 5: Analysis Agent] Cross-referencing {len(scraped_sources)} sources against claim...")
    analysis_output = run_analysis({"sources": scraped_sources, "claim": claim}, claim=claim)
    per_source = analysis_output.get("per_source", [])
    logger.info(f"[Step 5: Analysis Agent] Analysis produced {len(per_source)} evaluated sources: {per_source}")

    # ------------------------------------------------------------------------
    # STEP 6: Verdict & Explainer Agent (Person E)
    # ------------------------------------------------------------------------
    logger.info("[Step 6: Verdict Agent] Synthesizing final verdict and writing to RAG cache...")
    final_verdict = verdict_agent.generate_verdict(
        claim=claim,
        per_source=per_source,
        image_authenticity=None,
        language=detected_lang,
        write_to_rag=True
    )

    logger.info(f"=== [DeepFakeLens] Pipeline Completed. Final Verdict: {final_verdict.get('verdict')} (Confidence: {final_verdict.get('confidence')}) ===")
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
            for groq_model in ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama3-70b-8192"]:
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
