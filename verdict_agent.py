"""
Verdict & Explainer Agent (Agent 5 of DeepFakeLens Pipeline)

Role:
  Synthesizes cross-referenced evidence, source stances, credibility tiers,
  and optional image authenticity signals into a definitive fact-checking verdict,
  confidence score, non-expert explanation, and curated source list.

LLM Strategy:
  - Primary: Gemini 2.5 Flash (Google AI Studio)
  - Fallback: Groq Llama 3.3 70B
  - Local Rule-Based Mock: High-precision fallback when API keys are absent or during offline testing.

Output Contract:
  {
    "verdict": "true" | "false" | "misleading" | "unverified",
    "confidence": float (0.0 - 1.0),
    "explanation": string,
    "sources": [
      {"title": string, "url": string, "stance": "supports" | "contradicts" | "context"}
    ],
    "image_authenticity": {
      "is_ai_generated": bool,
      "confidence": float,
      "note": string
    } | null
  }
"""

from __future__ import annotations
import json
import logging
import os
import re
from typing import Any, Dict, List, Literal, Optional
from dotenv import load_dotenv

import rag_store

load_dotenv()

logger = logging.getLogger("DeepFakeLens.VerdictAgent")
logging.basicConfig(level=logging.INFO)

VerdictType = Literal["true", "false", "misleading", "unverified"]
StanceType = Literal["supports", "contradicts", "context"]
CredibilityTier = Literal["high", "medium", "low"]


SYSTEM_PROMPT = """You are the Verdict & Explainer Agent for DeepFakeLens, an AI fact-checking system.
Your job is to synthesize structured evidence and produce a final, definitive verdict.

CRITICAL RULES:
1. Verdict MUST be exactly one of: "true", "false", "misleading", "unverified".
2. Confidence MUST be a float between 0.0 and 1.0 based on source agreement, credibility tiers, and evidence quality.
3. Explanation MUST be plain-language, clear, neutral, and easily understood by a non-expert. Write in the requested language ({language}).
4. Sources MUST be formatted as a list of objects: [{"title": string, "url": string, "stance": "supports" | "contradicts" | "context"}].
5. If image_authenticity is provided and indicates AI generation with high confidence, factor this into the verdict and explanation.
6. Return ONLY valid JSON matching this schema:
{
  "verdict": "true" | "false" | "misleading" | "unverified",
  "confidence": 0.95,
  "explanation": "Plain language explanation here...",
  "sources": [
    {"title": "Source Title", "url": "https://...", "stance": "contradicts"}
  ]
}
"""


def _clean_json_output(raw_text: str) -> Dict[str, Any]:
    """Cleans and extracts JSON object from LLM response text."""
    text = raw_text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Regex search for the outermost {...} block
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Could not parse valid JSON from LLM output: {raw_text[:200]}")


def _rule_based_fallback_verdict(
    claim: str,
    per_source: List[Dict[str, Any]],
    image_authenticity: Optional[Dict[str, Any]] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    High-fidelity deterministic fallback when no LLM API keys are provided or network fails.
    Weighs source credibility tiers and stances.
    """
    tier_weights = {"high": 3.0, "medium": 1.5, "low": 0.5}
    stance_scores = {"supports": 0.0, "contradicts": 0.0, "context": 0.0}

    sources_formatted: List[Dict[str, str]] = []

    for src in per_source:
        url = src.get("url", "")
        title = src.get("title") or url.split("/")[2] if "//" in url else url or "Source"
        stance = src.get("stance", "context")
        tier = src.get("credibility_tier", "medium")

        weight = tier_weights.get(tier, 1.5)
        stance_scores[stance] = stance_scores.get(stance, 0.0) + weight

        sources_formatted.append({
            "title": str(title),
            "url": str(url),
            "stance": stance if stance in ("supports", "contradicts", "context") else "context"
        })

    is_ai_image = bool(image_authenticity and image_authenticity.get("is_ai_generated"))
    image_conf = float(image_authenticity.get("confidence", 0.0)) if image_authenticity else 0.0

    total_weight = sum(stance_scores.values())
    if is_ai_image and image_conf > 0.7:
        verdict: VerdictType = "false"
        confidence = min(0.95, max(0.85, image_conf))
        if language == "ar":
            explanation = f"الادعاء غير صحيح ومضلل. أظهر الفحص الجنائي الرقمي أن الصورة المرفقة تم إنشاؤها بواسطة الذكاء الاصطناعي بنسبة ثقة {int(confidence*100)}%."
        else:
            explanation = f"The claim is false and misleading. Digital forensic analysis confirmed the associated imagery is AI-generated (synthetic media) with {int(confidence*100)}% confidence."
    elif total_weight == 0:
        verdict = "unverified"
        confidence = 0.50
        if language == "ar":
            explanation = "لا توجد أدلة كافية أو مصادر موثوقة للتحقق من صحة هذا الادعاء بشكل قاطع."
        else:
            explanation = "There is insufficient evidence or reporting from verified sources to substantiate or disprove this claim."
    elif stance_scores["contradicts"] > stance_scores["supports"] * 1.5:
        verdict = "false"
        contradiction_ratio = stance_scores["contradicts"] / total_weight
        confidence = round(min(0.98, max(0.75, 0.70 + contradiction_ratio * 0.28)), 2)
        if language == "ar":
            explanation = f"الادعاء غير صحيح. أكدت التقارير والأدلة من المصادر الموثوقة أن المعلومات المذكورة غير دقيقة وتتعارض مع الحقائق المثبتة."
        else:
            explanation = f"The claim is false. Verified reports and authoritative sources directly contradict the assertion, confirming it is inaccurate."
    elif stance_scores["supports"] > stance_scores["contradicts"] * 1.5:
        verdict = "true"
        support_ratio = stance_scores["supports"] / total_weight
        confidence = round(min(0.98, max(0.75, 0.70 + support_ratio * 0.28)), 2)
        if language == "ar":
            explanation = f"الادعاء صحيح وموثق. تدعم الأدلة والمعلومات الصادرة عن جهات موثوقة صحة هذا الادعاء."
        else:
            explanation = f"The claim is verified and true. Multiple high-credibility sources and official records confirm the reported facts."
    elif stance_scores["supports"] > 0 and stance_scores["contradicts"] > 0:
        verdict = "misleading"
        confidence = 0.82
        if language == "ar":
            explanation = "الادعاء مضلل أو مجتزأ من سياقه؛ حيث يحتوي على بعض الحقائق لكنه تم تقديمه بطريقة مضللة."
        else:
            explanation = "The claim is misleading. While it may contain elements of truth, it lacks essential context or misrepresents key details."
    else:
        verdict = "unverified"
        confidence = 0.60
        if language == "ar":
            explanation = "الأدلة المتوفرة حالياً غير كافية لإصدار حكم نهائي بشأن صحة هذا الادعاء."
        else:
            explanation = "Available evidence from checked sources provides context but is currently inconclusive."

    return {
        "verdict": verdict,
        "confidence": confidence,
        "explanation": explanation,
        "sources": sources_formatted,
        "image_authenticity": image_authenticity
    }


def _call_gemini(prompt: str, language: str) -> Dict[str, Any]:
    """Calls Gemini with primary and compatible fallback models."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=7.0))
    system_instruction = SYSTEM_PROMPT.replace("{language}", "Arabic" if language == "ar" else "English")

    gemini_models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-3.7-flash", "gemini-flash-latest"]
    last_error = None

    for model in gemini_models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                logger.info(f"Gemini responded using model: {model}")
                return _clean_json_output(response.text)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Gemini model calls failed. Last error: {last_error}")


def _call_groq(prompt: str, language: str) -> Dict[str, Any]:
    """Calls Groq with primary Llama 3.3 and high-speed fallback models."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set.")

    from groq import Groq

    client = Groq(api_key=api_key, timeout=7.0)
    system_instruction = SYSTEM_PROMPT.replace("{language}", "Arabic" if language == "ar" else "English")

    groq_models = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound"]
    last_error = None

    for model in groq_models:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = chat_completion.choices[0].message.content
            if content:
                logger.info(f"Groq responded using model: {model}")
                return _clean_json_output(content)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Groq model calls failed. Last error: {last_error}")


def generate_verdict(
    claim: str,
    per_source: List[Dict[str, Any]],
    image_authenticity: Optional[Dict[str, Any]] = None,
    language: str = "en",
    write_to_rag: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for Verdict Agent.
    Executes Gemini 2.5 Flash -> Groq Llama 3.3 70B -> Rule-based fallback.
    Validates output schema and writes back to RAG cache.
    """
    user_payload = {
        "claim": claim,
        "per_source": per_source,
        "image_authenticity": image_authenticity,
        "target_language": language
    }
    prompt = f"Analyze the following fact-checking evidence and generate the final verdict JSON:\n{json.dumps(user_payload, indent=2, ensure_ascii=False)}"

    result: Optional[Dict[str, Any]] = None
    llm_used = "none"

    # Step 1: Try Primary (Gemini 2.5 Flash)
    if os.environ.get("GEMINI_API_KEY"):
        try:
            logger.info("Executing Verdict Agent with Primary LLM (Gemini 2.5 Flash)...")
            result = _call_gemini(prompt, language)
            llm_used = "gemini-2.5-flash"
        except Exception as e:
            logger.warning(f"Primary Gemini call failed: {e}. Falling back to Groq...")

    # Step 2: Try Fallback (Groq Llama 3.3 70B)
    if result is None and os.environ.get("GROQ_API_KEY"):
        try:
            logger.info("Executing Verdict Agent with Fallback LLM (Groq Llama 3.3 70B)...")
            result = _call_groq(prompt, language)
            llm_used = "groq-llama-3.3-70b"
        except Exception as e:
            logger.warning(f"Fallback Groq call failed: {e}. Falling back to local synthesis...")

    # Step 3: Local Rule-Based Mock Fallback
    if result is None:
        logger.info("Using deterministic local rule-based synthesis for verdict...")
        result = _rule_based_fallback_verdict(claim, per_source, image_authenticity, language)
        llm_used = "local-deterministic-engine"

    # Enforce and normalize output schema
    verdict = str(result.get("verdict", "unverified")).lower().strip()
    if verdict not in ("true", "false", "misleading", "unverified"):
        verdict = "unverified"

    confidence = float(result.get("confidence", 0.70))
    confidence = max(0.0, min(1.0, confidence))

    explanation = str(result.get("explanation", "")).strip()
    if not explanation:
        explanation = "Verdict synthesized from analyzed evidence sources."

    # Normalize sources from LLM result or per_source input
    sources_raw = result.get("sources")
    if not isinstance(sources_raw, list) or len(sources_raw) == 0:
        sources_raw = []
        for s in per_source:
            url = s.get("url", "")
            title = s.get("title") or (url.split("/")[2] if "//" in url else url) or "Evidence Source"
            stance = s.get("stance", "context")
            sources_raw.append({"title": title, "url": url, "stance": stance})

    sources_cleaned: List[Dict[str, str]] = []
    for s in sources_raw:
        if isinstance(s, dict):
            url = str(s.get("url", ""))
            title = str(s.get("title", url or "Source"))
            stance = str(s.get("stance", "context")).lower().strip()
            if stance not in ("supports", "contradicts", "context"):
                stance = "context"
            sources_cleaned.append({
                "title": title,
                "url": url,
                "stance": stance
            })

    final_output: Dict[str, Any] = {
        "verdict": verdict,
        "confidence": confidence,
        "explanation": explanation,
        "sources": sources_cleaned,
        "image_authenticity": image_authenticity
    }

    logger.info(f"Verdict generated successfully [Engine: {llm_used}, Verdict: {verdict}, Conf: {confidence}]")

    # Step 4: Write-back to RAG Cache
    if write_to_rag:
        try:
            rag_store.write_to_cache(claim, final_output)
            logger.info("Verdict successfully written to RAG knowledge cache.")
        except Exception as e:
            logger.warning(f"Failed to write verdict to RAG store: {e}")

    return final_output


if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "mock_input.json"
    print(f"--- Running Verdict Agent standalone with '{input_file}' ---")

    if os.path.exists(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "claim": "Sample claim for standalone test",
            "per_source": [
                {"url": "https://example.com/debunk", "title": "Example Debunk", "stance": "contradicts", "credibility_tier": "high"}
            ],
            "image_authenticity": None,
            "language": "en"
        }

    output = generate_verdict(
        claim=data.get("claim", ""),
        per_source=data.get("per_source", []),
        image_authenticity=data.get("image_authenticity"),
        language=data.get("language", "en")
    )
    print("\nFinal Pipeline Output JSON:")
    print(json.dumps(output, indent=2, ensure_ascii=False))
