# DeepFakeLens — Cross-Reference / Analysis Agent

The **Cross-Reference / Analysis Agent** is a pure reasoning agent in the 5-agent DeepFakeLens pipeline. It cross-references extracted claims against scraped source texts, assigns credibility tiers to sources using a deterministic domain tier list, and classifies the stance of each source using Gemini 2.5 Flash with Groq Llama 3.3 70B fallback.

---

## 1. Responsibilities & Architecture

1. **No External Scraping or Search Tools**: Pure reasoning over structured inputs.
2. **Hardcoded Credibility Tiering**:
   - `high`: Major global wire services (Reuters, AP, AFP, BBC), primary IFCN fact-checkers (Snopes, PolitiFact, FactCheck.org), `.gov`, `.edu`, `.mil`, and official intergovernmental organizations.
   - `medium`: Mainstream national/regional news (CNN, Forbes, The Hindu, SCMP) and reputable tech/science publications (TechCrunch, Wired, Nature).
   - `low`: Unrecognized domains, blogs (`blogspot`, `medium`), user-generated content, forums, and social media platforms.
3. **Stance Classification**:
   - `supports`: Source validates or affirms the claim with evidence.
   - `contradicts`: Source refutes, debunks, or proves the claim is fake/false.
   - `context`: Source provides relevant topical background without confirming or denying the core claim.
4. **Primary & Fallback LLM**:
   - Primary: **Gemini 2.5 Flash** (`GEMINI_API_KEY` or `GOOGLE_API_KEY`)
   - Fallback: **Groq Llama 3.3 70B** (`GROQ_API_KEY`)
   - Offline Mode: Deterministic heuristic classifier for zero-dependency local testing.

---

## 2. Locked JSON Contract

### Input Contract (from Scraper Agent):
```json
{
  "claim": "The CEO of GlobalTech announced his immediate resignation and admitted to massive financial fraud in a leaked internal video broadcast.",
  "sources": [
    {
      "url": "https://www.reuters.com/fact-check/globaltech-ceo-resignation-video-is-deepfake-manipulated-media-2026",
      "title": "Fact Check: Leaked video of GlobalTech CEO resigning and admitting fraud is an AI deepfake",
      "clean_text": "Reuters Fact Check investigated the viral video circulating on social media claiming..."
    }
  ]
}
```

### Output Contract:
```json
{
  "per_source": [
    {
      "url": "https://www.reuters.com/fact-check/globaltech-ceo-resignation-video-is-deepfake-manipulated-media-2026",
      "stance": "contradicts",
      "credibility_tier": "high"
    },
    {
      "url": "https://tech-leakz-daily.blogspot.com/2026/08/explosive-globaltech-ceo-steps-down-admits-fraud.html",
      "stance": "supports",
      "credibility_tier": "low"
    },
    {
      "url": "https://techcrunch.com/2026/08/25/deepfake-executive-impersonation-scams-rise-across-tech-enterprises/",
      "stance": "context",
      "credibility_tier": "medium"
    }
  ]
}
```

---

## 3. Running Standalone

### Execute Mock Run:
```bash
python analysis_agent.py mock_input.json
```

### Run Unit & Integration Tests:
```bash
python test_analysis_agent.py
```

### Environment Variables (Optional for live LLM inference):
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export GROQ_API_KEY="your-groq-api-key"
```
