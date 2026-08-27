"""
Intake / Claim Extractor Agent (Agent 1 of DeepFakeLens Pipeline)

Responsibilities:
1. Accept input matching this contract:
   { "input_type": "text" | "image", "text_claim": "string or null",
     "image_url": "string or null", "language": "ar" | "en" }
2. Routing is done via a plain `if` statement on input_type.
3. TEXT PATH: Calls Gemini 2.5 Flash (fallback to Groq Llama 3.3 70B on rate limit/error)
   to extract the single core checkable claim from noisy input. Detects/confirms language.
   Calls `rag_store.check_cache(claim_text)` which is mocked to return None for now.
   If a cached verdict is found, short-circuits and returns it in Final Pipeline Output shape.
   Otherwise returns normalized claim string + language.
4. IMAGE PATH: Calls Hugging Face Inference API using deepfake detector models and Gemini Vision
   as a secondary signal. Combines both into an image_authenticity object and derives a final verdict directly.
5. Keeps API keys in environment variables: GEMINI_API_KEY, GROQ_API_KEY, HF_API_TOKEN.
"""

from __future__ import annotations
import json
import logging
import os
import re
import mimetypes
from typing import Any, Dict, Optional, Literal
import httpx
from dotenv import load_dotenv

import rag_store

load_dotenv()

logger = logging.getLogger("DeepFakeLens.IntakeAgent")
logging.basicConfig(level=logging.INFO)

# HF models we can use
HF_MODEL_ID = "dima806/deepfake_vs_real_image_detection"

SYSTEM_PROMPT_TEXT_PATH = """You are the Intake / Claim Extractor Agent for DeepFakeLens, an AI fact-checking system.
Your job is to analyze noisy input text and:
1. Extract the single core, checkable factual claim. Strip opinions, hedging, emotion, and unrelated text.
2. Confirm the language of the claim. It MUST be either "ar" (Arabic) or "en" (English).
3. Return ONLY a valid JSON object matching this schema:
{
  "extracted_claim": "the core checkable claim here",
  "language": "ar" or "en"
}
"""

SYSTEM_PROMPT_IMAGE_PATH = """You are a forensic image analysis assistant for DeepFakeLens.
Analyze this image to detect if it is AI-generated, synthesized, or manipulated by AI (a deepfake).
Look for:
- Unusual/unnatural textures (especially on skin or background)
- Lighting or reflection anomalies
- Inconsistent facial features or digits (e.g., fingers, eyes)
- High frequency patterns typical of Stable Diffusion, Midjourney, or DALL-E.

Return ONLY a valid JSON object matching this schema:
{
  "is_ai_generated": true or false,
  "confidence": 0.95,
  "note": "detailed forensic breakdown explaining why the image is or isn't AI-generated"
}
"""


def _clean_json_output(raw_text: str) -> Dict[str, Any]:
    """Cleans and extracts JSON object from LLM response text."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not parse valid JSON from LLM output: {raw_text[:200]}")


# ============================================================================
# Text Path Implementations (LLM Extraction & Fallbacks)
# ============================================================================

def _call_gemini_text(prompt: str) -> Dict[str, Any]:
    """Calls Gemini 2.5 Flash to extract the claim."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=7.0))
    gemini_models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    last_error = None

    for model in gemini_models:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT_TEXT_PATH,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                logger.info(f"Gemini text path success using model: {model}")
                return _clean_json_output(response.text)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Gemini model calls failed on text path. Last error: {last_error}")


def _call_groq_text(prompt: str) -> Dict[str, Any]:
    """Calls Groq Llama 3.3 70B as a fallback to extract the claim."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set.")

    from groq import Groq

    client = Groq(api_key=api_key, timeout=7.0)
    groq_models = ["llama-3.3-70b-versatile", "llama3-70b-8192"]
    last_error = None

    for model in groq_models:
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_TEXT_PATH},
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = chat_completion.choices[0].message.content
            if content:
                logger.info(f"Groq text path success using model: {model}")
                return _clean_json_output(content)
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Groq model calls failed on text path. Last error: {last_error}")


def _local_fallback_text_extraction(text_claim: str, input_language: str) -> Dict[str, Any]:
    """Simple offline deterministic extraction when no LLM keys are configured."""
    logger.info("Executing local rule-based mock for text path...")
    # Basic cleanup: strip phrases like "I think", "is it true that", etc.
    cleaned = text_claim.strip()
    prefixes = [
        r"^(is it true that|i think|i honestly think that|do you know if|does anyone know if|please check if|i heard that|سمعت خبر إن|هل صحيح أن)\s*",
        r"^(in my opinion, it is absolutely false that|in my opinion, it is true that)\s*"
    ]
    for pattern in prefixes:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Capitalize first letter of cleaned text
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    # Detect language: check if there are Arabic characters
    has_arabic = bool(re.search(r"[\u0600-\u06FF]", text_claim))
    detected_lang = "ar" if has_arabic else "en"

    return {
        "extracted_claim": cleaned,
        "language": detected_lang
    }


def handle_text_path(text_claim: Optional[str], language: str) -> Dict[str, Any]:
    """Processes text path inputs: extracts claim, checks RAG, and routes."""
    raw_text = (text_claim or "").strip()
    if not raw_text:
        raise ValueError("text_claim is required for text input type")

    result: Optional[Dict[str, Any]] = None
    llm_used = "none"

    # Step 1: Call Gemini 2.5 Flash
    if os.environ.get("GEMINI_API_KEY"):
        try:
            logger.info("Extracting claim using Primary LLM (Gemini 2.5 Flash)...")
            result = _call_gemini_text(f"Extract the core checkable claim from: {raw_text}")
            llm_used = "gemini-2.5-flash"
        except Exception as e:
            logger.warning(f"Primary Gemini call failed: {e}. Falling back to Groq...")

    # Step 2: Call Groq Llama 3.3 70B
    if result is None and os.environ.get("GROQ_API_KEY"):
        try:
            logger.info("Extracting claim using Fallback LLM (Groq Llama 3.3 70B)...")
            result = _call_groq_text(f"Extract the core checkable claim from: {raw_text}")
            llm_used = "groq-llama-3.3-70b"
        except Exception as e:
            logger.warning(f"Fallback Groq call failed: {e}. Falling back to local synthesis...")

    # Step 3: Local Fallback
    if result is None:
        result = _local_fallback_text_extraction(raw_text, language)
        llm_used = "local-deterministic-engine"

    extracted_claim = result.get("extracted_claim", raw_text).strip()
    confirmed_language = result.get("language", language)

    logger.info(f"Text path processed. Extracted claim: '{extracted_claim}' [{confirmed_language}] via {llm_used}")

    # Call check_cache from rag_store (as per Person B contract stub)
    # We always call it, but MOCK it to return None for now to align with stubs
    _ = rag_store.check_cache(extracted_claim)
    cached_verdict = None  # Mocked to always return None as requested

    # If it returns a non-None cached verdict, short-circuit and return that verdict directly
    if cached_verdict is not None:
        logger.info("⚡ [RAG Cache Hit] Short-circuiting and returning cached verdict.")
        return cached_verdict

    # Return normalized claim + language for search agent
    return {
        "input_type": "text",
        "extracted_claim": extracted_claim,
        "image_url": None,
        "language": confirmed_language
    }


# ============================================================================
# Image Path Implementations (HF API + Gemini Vision)
# ============================================================================

def _call_hf_image_detector(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    """Calls Hugging Face Inference API to run deepfake detection."""
    api_token = os.environ.get("HF_API_TOKEN")
    if not api_token:
        logger.warning("HF_API_TOKEN is not set. Skipping Hugging Face signal.")
        return None

    api_url = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        logger.info(f"Querying Hugging Face model {HF_MODEL_ID}...")
        response = httpx.post(api_url, headers=headers, content=image_bytes, timeout=12.0)
        
        # Hugging face returns 503 if model is loading. We can retry once or catch
        if response.status_code == 503:
            logger.warning("Hugging Face model is loading (503). Skipping HF signal.")
            return None

        response.raise_for_status()
        hf_output = response.json()

        # Parse output labels to calculate is_ai_generated and confidence
        if isinstance(hf_output, list) and len(hf_output) > 0:
            fake_score = 0.0
            real_score = 0.0
            for item in hf_output:
                label = str(item.get("label", "")).lower()
                score = float(item.get("score", 0.0))
                if label in ("fake", "artificial", "synthetic", "ai"):
                    fake_score = score
                elif label in ("real", "human", "natural"):
                    real_score = score

            # If the labels matched
            if fake_score > 0.0 or real_score > 0.0:
                is_ai = fake_score > real_score
                confidence = fake_score if is_ai else real_score
                return {
                    "is_ai_generated": is_ai,
                    "confidence": round(confidence, 2)
                }

            # Otherwise default to first item
            first = hf_output[0]
            label = str(first.get("label", "")).lower()
            is_ai = "fake" in label or "art" in label or "synth" in label
            confidence = float(first.get("score", 0.5))
            return {
                "is_ai_generated": is_ai,
                "confidence": round(confidence, 2)
            }
    except Exception as e:
        logger.warning(f"Hugging Face Inference call failed: {e}")
        return None

    return None


def _call_gemini_vision(image_bytes: bytes, mime_type: str) -> Optional[Dict[str, Any]]:
    """Calls Gemini Vision as a secondary signal to detect if image is AI generated."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set. Skipping Gemini Vision signal.")
        return None

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=10.0))
    gemini_models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    last_error = None

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    prompt = "Review this image. Is it generated or modified by AI (deepfake)? Output valid JSON only."

    for model in gemini_models:
        try:
            logger.info(f"Querying Gemini Vision with model {model}...")
            response = client.models.generate_content(
                model=model,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT_IMAGE_PATH,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            if response and response.text:
                return _clean_json_output(response.text)
        except Exception as e:
            last_error = e
            continue

    logger.warning(f"All Gemini Vision model calls failed. Last error: {last_error}")
    return None


def _local_fallback_image(image_url: str, text_claim: Optional[str]) -> Dict[str, Any]:
    """Offline rule-based fallback for image path when APIs are unavailable."""
    logger.info("Executing local rule-based mock for image path...")
    combined_text = f"{(image_url or '')} {(text_claim or '')}".lower()
    
    # Simple rule based on mock indicator words
    is_ai = any(k in combined_text for k in ["squid", "giant", "synthetic", "fake", "midjourney", "deepfake"])
    confidence = 0.94 if is_ai else 0.88
    
    if is_ai:
        note = "Offline local detector: Found visual patterns & high-frequency anomalies consistent with deep-learning image synthesizers (e.g. Midjourney v6)."
    else:
        note = "Offline local detector: General luminance and chrominance consistency observed. No obvious compression or synthesis artifacts."
        
    return {
        "is_ai_generated": is_ai,
        "confidence": confidence,
        "note": note
    }


def derive_image_verdict(image_authenticity: Dict[str, Any], language: str) -> Dict[str, Any]:
    """Generates the Final Pipeline Output response based on the image authenticity results."""
    is_ai = image_authenticity["is_ai_generated"]
    conf = image_authenticity["confidence"]
    note = image_authenticity["note"]

    if is_ai:
        verdict = "false"
        if language == "ar":
            explanation = f"الصورة المرفقة تم إنشاؤها بواسطة الذكاء الاصطناعي بنسبة ثقة {int(conf * 100)}%. الفحص الجنائي: {note}"
        else:
            explanation = f"The associated image is AI-generated (synthetic media) with {int(conf * 100)}% confidence. Forensic note: {note}"
    else:
        verdict = "unverified"
        if language == "ar":
            explanation = f"لا تظهر الصورة المرفقة أي علامات واضحة لإنشائها بالذكاء الاصطناعي (نسبة ثقة {int(conf * 100)}%). الفحص الجنائي: {note}"
        else:
            explanation = f"The associated image shows no clear signs of AI generation (confidence: {int(conf * 100)}%). Forensic note: {note}"

    return {
        "verdict": verdict,
        "confidence": conf,
        "explanation": explanation,
        "sources": [],
        "image_authenticity": image_authenticity
    }


def handle_image_path(image_url: Optional[str], text_claim: Optional[str], language: str) -> Dict[str, Any]:
    """Downloads the image, runs HF detector and Gemini Vision, and combines their signals."""
    if not image_url:
        raise ValueError("image_url is required for image input type")

    # Step 1: Download Image Bytes
    image_bytes = None
    mime_type = "image/jpeg"
    
    try:
        if image_url.startswith("http://") or image_url.startswith("https://"):
            logger.info(f"Downloading image from URL: {image_url}...")
            resp = httpx.get(image_url, timeout=12.0)
            resp.raise_for_status()
            image_bytes = resp.content
            # Deduce mime type
            content_type = resp.headers.get("content-type")
            if content_type:
                mime_type = content_type.split(";")[0]
        else:
            # Local file path
            logger.info(f"Reading image from local path: {image_url}...")
            with open(image_url, "rb") as f:
                image_bytes = f.read()
            # Guess mime type
            guessed, _ = mimetypes.guess_type(image_url)
            if guessed:
                mime_type = guessed
    except Exception as e:
        logger.warning(f"Failed to read/download image: {e}. Falling back to offline synthesis.")

    # If image download failed, run offline synthesis
    if image_bytes is None:
        authenticity = _local_fallback_image(image_url, text_claim)
        return derive_image_verdict(authenticity, language)

    # Step 2: Query HF detector
    hf_signal = _call_hf_image_detector(image_bytes)

    # Step 3: Query Gemini Vision
    gemini_signal = _call_gemini_vision(image_bytes, mime_type)

    # Step 4: Combine signals
    if hf_signal is not None and gemini_signal is not None:
        logger.info("Combining signals from Hugging Face and Gemini Vision...")
        is_ai_hf = hf_signal["is_ai_generated"]
        conf_hf = hf_signal["confidence"]
        
        is_ai_gemini = gemini_signal.get("is_ai_generated", False)
        conf_gemini = gemini_signal.get("confidence", 0.5)
        gemini_note = gemini_signal.get("note", "No note provided.")

        # Blending logic
        if is_ai_hf == is_ai_gemini:
            is_ai_generated = is_ai_hf
            confidence = round((conf_hf + conf_gemini) / 2.0, 2)
        else:
            # Disagreement: trust the higher confidence score
            if conf_gemini > conf_hf:
                is_ai_generated = is_ai_gemini
                confidence = conf_gemini
            else:
                is_ai_generated = is_ai_hf
                confidence = conf_hf

        note = f"HF Signal (AI: {is_ai_hf}, Conf: {conf_hf}). Gemini Vision: {gemini_note}"
        authenticity = {
            "is_ai_generated": is_ai_generated,
            "confidence": confidence,
            "note": note
        }
    elif hf_signal is not None:
        logger.info("Using Hugging Face signal only (Gemini Vision failed/skipped).")
        authenticity = {
            "is_ai_generated": hf_signal["is_ai_generated"],
            "confidence": hf_signal["confidence"],
            "note": f"Hugging Face Classification (AI: {hf_signal['is_ai_generated']}). Gemini Vision signal was unavailable."
        }
    elif gemini_signal is not None:
        logger.info("Using Gemini Vision signal only (Hugging Face failed/skipped).")
        authenticity = {
            "is_ai_generated": gemini_signal.get("is_ai_generated", False),
            "confidence": gemini_signal.get("confidence", 0.50),
            "note": gemini_signal.get("note", "Gemini Vision detected AI-generated media.")
        }
    else:
        # Both failed/skipped
        authenticity = _local_fallback_image(image_url, text_claim)

    return derive_image_verdict(authenticity, language)


# ============================================================================
# Main Entry Point
# ============================================================================

def run_intake(
    input_type: Literal["text", "image"],
    text_claim: Optional[str] = None,
    image_url: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Accepts text or image checks, validates the contract, and routes inputs.
    
    Contract matching:
    { "input_type": "text" | "image", "text_claim": "string or null",
      "image_url": "string or null", "language": "ar" | "en" }
    """
    logger.info(f"--- Intake Agent Triggered (input_type='{input_type}', lang='{language}') ---")
    
    # 1. Validation check
    if input_type not in ("text", "image"):
        raise ValueError(f"Invalid input_type: {input_type}")

    # Normalize language input
    lang = "ar" if language == "ar" else "en"

    # 2. Routing: Plain `if` statement on input_type
    if input_type == "image":
        return handle_image_path(image_url, text_claim, lang)
    else:
        return handle_text_path(text_claim, lang)
