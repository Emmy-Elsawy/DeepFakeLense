"""
DeepFakeLens - Cross-Reference / Analysis Agent
File: analysis_agent.py

Responsibilities:
1. Pure reasoning agent: compares an extracted claim against scraped sources' clean_text.
2. Classifies stance as 'supports' | 'contradicts' | 'context' using Gemini 2.5 Flash
   with fallback to Groq Llama 3.3 70B.
3. Assigns each source a credibility_tier ('high' | 'medium' | 'low') using a hardcoded
   trusted-domain tier list.
4. Produces locked JSON output matching pipeline contract:
   {
     "per_source": [
       {
         "url": "string",
         "stance": "supports" | "contradicts" | "context",
         "credibility_tier": "high" | "medium" | "low"
       }
     ]
   }
"""

import json
import logging
import os
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Literal, Optional

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AnalysisAgent")

# Type aliases for strict contract conformance
StanceType = Literal["supports", "contradicts", "context"]
CredibilityTierType = Literal["high", "medium", "low"]

# ==============================================================================
# 1. HARDCODED TRUSTED DOMAIN TIER LIST
# ==============================================================================

# High-credibility: Top international wire services, public broadcasters,
# government / official academic institutions, and recognized primary fact-checking bodies.
HIGH_CREDIBILITY_DOMAINS = {
    # Global Wire Services & Major Investigative Outlets
    "reuters.com",
    "apnews.com",
    "afp.com",
    "bbc.com",
    "bbc.co.uk",
    "aljazeera.com",
    "bloomberg.com",
    "npr.org",
    "pbs.org",
    "theguardian.com",
    "nytimes.com",
    "washingtonpost.com",
    "wsj.com",
    "ft.com",
    "economist.com",
    # Primary Fact-Checking Organizations (IFCN Signatories)
    "snopes.com",
    "politifact.com",
    "factcheck.org",
    "aap.com.au",
    "fullfact.org",
    "checkyourfact.com",
    "leadstories.com",
    "africacheck.org",
    "altnews.in",
    "boomlive.in",
    # Major International Intergovernmental Agencies
    "who.int",
    "un.org",
    "interpol.int",
    "europa.eu",
}

# High-credibility domain suffix rules (gov, edu, etc.)
HIGH_CREDIBILITY_SUFFIXES = (
    ".gov",
    ".gov.uk",
    ".gov.au",
    ".gov.in",
    ".gov.ca",
    ".edu",
    ".edu.au",
    ".ac.uk",
    ".mil",
)

# Medium-credibility: Reputable mainstream national/regional news outlets,
# established technology journals, and prominent editorial publications.
MEDIUM_CREDIBILITY_DOMAINS = {
    # Mainstream News & National Outlets
    "cnn.com",
    "nbcnews.com",
    "cbsnews.com",
    "abcnews.go.com",
    "usatoday.com",
    "forbes.com",
    "time.com",
    "thehill.com",
    "axios.com",
    "politico.com",
    "dw.com",
    "france24.com",
    "scmp.com",
    "hindustantimes.com",
    "thehindu.com",
    "indianexpress.com",
    "smh.com.au",
    "theage.com.au",
    "cbc.ca",
    "theconversation.com",
    "euronews.com",
    "channelnewsasia.com",
    "japantimes.co.jp",
    # Reputable Science, Tech & Industry Publications
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "nature.com",
    "scientificamerican.com",
    "arstechnica.com",
    "engadget.com",
    "zdnet.com",
    "cnet.com",
    "technologyreview.com",
    "newscientist.com",
}


def extract_domain(url: str) -> str:
    """Extract and normalize host domain from a given URL."""
    if not url:
        return ""
    try:
        # Prepend scheme if missing for urlparse
        if not re.match(r"^[a-zA-Z]+://", url):
            url = "http://" + url
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
    except Exception as e:
        logger.warning(f"Error parsing domain from url '{url}': {e}")
        return ""


def get_credibility_tier(url: str) -> CredibilityTierType:
    """
    Assign a credibility tier ('high' | 'medium' | 'low') based on a hardcoded
    trusted-domain tier list. No ML scoring is used.
    """
    domain = extract_domain(url)
    if not domain:
        return "low"

    # Check high-credibility suffixes (e.g. .gov, .edu)
    for suffix in HIGH_CREDIBILITY_SUFFIXES:
        if domain.endswith(suffix):
            return "high"

    # Check exact match or subdomains of high-credibility domains
    for high_domain in HIGH_CREDIBILITY_DOMAINS:
        if domain == high_domain or domain.endswith("." + high_domain):
            return "high"

    # Check exact match or subdomains of medium-credibility domains
    for med_domain in MEDIUM_CREDIBILITY_DOMAINS:
        if domain == med_domain or domain.endswith("." + med_domain):
            return "medium"

    # Unrecognized domains, user blogs, forums, social media, etc.
    return "low"


# ==============================================================================
# 2. LLM CLIENTS & STANCE CLASSIFICATION (Gemini 2.5 Flash -> Groq Fallback)
# ==============================================================================

STANCE_PROMPT_TEMPLATE = """You are the Cross-Reference and Analysis Agent for DeepFakeLens, an automated fact-checking pipeline.

Task:
Compare the given TARGET CLAIM against the provided SOURCE TEXT and classify the stance of the source relative to the claim into exactly ONE of the following 3 categories:

Categories:
1. "supports": The source explicitly validates, confirms, asserts, or provides evidence that the claim is true.
2. "contradicts": The source directly refutes, debunks, disproves, denies, or provides evidence that the claim is false, fake, fabricated, or inaccurate.
3. "context": The source discusses related background, topics, entities, or general context, but does NOT directly confirm or refute the core claim.

TARGET CLAIM:
\"\"\"{claim}\"\"\"

SOURCE TEXT:
\"\"\"{clean_text}\"\"\"

Respond STRICTLY with a valid JSON object matching this schema:
{{
  "stance": "supports" | "contradicts" | "context",
  "reason": "<one sentence internal explanation for debugging>"
}}
"""


def _call_gemini(claim: str, clean_text: str, api_key: str) -> Optional[Dict[str, str]]:
    """Primary LLM call: Gemini 2.5 Flash via standard REST API."""
    import urllib.error
    import urllib.request

    # Gemini API endpoint for gemini-2.5-flash
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    prompt = STANCE_PROMPT_TEMPLATE.format(
        claim=claim.strip(),
        clean_text=clean_text.strip()[:4000],  # Truncate source text safely if overly long
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidate_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(candidate_text)
            stance = parsed.get("stance", "").lower().strip()
            if stance in ("supports", "contradicts", "context"):
                return {"stance": stance, "reason": parsed.get("reason", "")}
    except Exception as e:
        logger.warning(f"Gemini API call failed ({e}); attempting fallback...")
    return None


def _call_groq(claim: str, clean_text: str, api_key: str) -> Optional[Dict[str, str]]:
    """Fallback LLM call: Groq Llama 3.3 70B via OpenAI-compatible endpoint."""
    import urllib.error
    import urllib.request

    url = "https://api.groq.com/openai/v1/chat/completions"
    model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    prompt = STANCE_PROMPT_TEMPLATE.format(
        claim=claim.strip(),
        clean_text=clean_text.strip()[:4000],
    )

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise fact-checking assistant that outputs valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content_text = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content_text)
            stance = parsed.get("stance", "").lower().strip()
            if stance in ("supports", "contradicts", "context"):
                return {"stance": stance, "reason": parsed.get("reason", "")}
    except Exception as e:
        logger.warning(f"Groq API call failed ({e}); attempting local heuristic fallback...")
    return None


def _deterministic_heuristic_fallback(claim: str, clean_text: str) -> Dict[str, str]:
    """
    Deterministic rule-based stance classification fallback for standalone mock testing
    and offline execution when API keys are absent or network requests are unavailable.
    """
    text_lower = clean_text.lower()

    # Contradiction indicators (debunking, false, deepfake, fabricated, unverified)
    contradiction_regexes = [
        r"\bis (an? )?(ai )?deepfake\b",
        r"\bdebunk(ed|ing|s)?\b",
        r"\b(is|was) (false|fake|fabricated|manipulated|untrue)\b",
        r"\bfact check:?\b",
        r"\bmanipulated media\b",
        r"\bhoax\b",
        r"\bnever made the statements\b",
        r"\bremains in office\b",
        r"\bsynthetic speech\b",
        r"\bfacial warping\b",
        r"\bno evidence\b",
        r"\bincorrectly claimed\b",
        r"\bdenied\b",
        r"\bdisproven\b",
        r"\brefuted\b",
    ]

    # Support indicators
    support_regexes = [
        r"\bresigned immediately\b",
        r"\bsteps down\b",
        r"\badmitting to (massive )?(\$\d+|financial|fraud)\b",
        r"\badmitted to\b",
        r"\bconfirmed the resignation\b",
        r"\bannounced his immediate resignation\b",
        r"\binsiders confirm\b",
        r"\bshocking turn of events\b",
    ]

    has_contradiction = any(re.search(p, text_lower) for p in contradiction_regexes)
    has_support = any(re.search(p, text_lower) for p in support_regexes)

    if has_contradiction:
        return {
            "stance": "contradicts",
            "reason": "Source explicitly reports fact-check, debunking, or indicators that the claim is fake/false.",
        }
    elif has_support:
        return {
            "stance": "supports",
            "reason": "Source affirms and repeats the claim as true.",
        }
    else:
        return {
            "stance": "context",
            "reason": "Source provides related topical background without directly validating or refuting the claim.",
        }


def classify_stance(claim: str, clean_text: str) -> StanceType:
    """
    Classify the stance of a source relative to a claim using:
    1. Primary: Gemini 2.5 Flash
    2. Fallback: Groq Llama 3.3 70B
    3. Standalone / Mock: Offline heuristic fallback
    """
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        result = _call_gemini(claim, clean_text, gemini_key)
        if result and result.get("stance") in ("supports", "contradicts", "context"):
            return result["stance"]  # type: ignore

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        result = _call_groq(claim, clean_text, groq_key)
        if result and result.get("stance") in ("supports", "contradicts", "context"):
            return result["stance"]  # type: ignore

    # If no keys or network calls fail, use deterministic fallback
    logger.info("Using offline heuristic classification fallback.")
    result = _deterministic_heuristic_fallback(claim, clean_text)
    return result["stance"]  # type: ignore


# ==============================================================================
# 3. CORE ANALYSIS AGENT PIPELINE
# ==============================================================================

class AnalysisAgent:
    """
    Cross-Reference / Analysis Agent for DeepFakeLens.
    Processes structured source inputs, assigns credibility tiers, and classifies stances.
    """

    def __init__(self):
        pass

    def run(self, input_data: Dict[str, Any], claim: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute analysis on input data.

        Input schema:
        {
          "claim": "string" (optional if passed via claim argument),
          "sources": [
            {
              "url": "string",
              "title": "string",
              "clean_text": "string"
            }
          ]
        }

        Output schema (Locked Contract):
        {
          "per_source": [
            {
              "url": "string",
              "stance": "supports" | "contradicts" | "context",
              "credibility_tier": "high" | "medium" | "low"
            }
          ]
        }
        """
        target_claim = claim or input_data.get("claim", "")
        sources = input_data.get("sources", [])

        if not target_claim and sources:
            # Check if claim is nested or infer from first source title as fallback
            target_claim = input_data.get("extracted_claim", "")

        per_source_results: List[Dict[str, Any]] = []

        for src in sources:
            url = src.get("url", "")
            clean_text = src.get("clean_text", "")

            # 1. Assign credibility tier via hardcoded domain tier list
            cred_tier = get_credibility_tier(url)

            # 2. Classify stance (Gemini 2.5 Flash -> Groq -> Heuristic fallback)
            stance = classify_stance(target_claim, clean_text)

            per_source_results.append({
                "url": url,
                "stance": stance,
                "credibility_tier": cred_tier,
            })

        output = {
            "per_source": per_source_results
        }
        return output


def run_analysis(input_data: Dict[str, Any], claim: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to run AnalysisAgent."""
    agent = AnalysisAgent()
    return agent.run(input_data, claim)


# ==============================================================================
# 4. STANDALONE CLI ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DeepFakeLens Analysis Agent")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="mock_input.json",
        help="Path to mock input JSON file (default: mock_input.json)",
    )
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    agent = AnalysisAgent()
    result = agent.run(data)

    print("\n" + "=" * 50)
    print("ANALYSIS AGENT RESULT (JSON Contract):")
    print("=" * 50)
    print(json.dumps(result, indent=2))
