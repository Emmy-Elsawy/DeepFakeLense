# DeepFakeLens — Implementation Plan (imp.md)

A multi-agent AI fact-checking system. A user submits a text claim or an image; a pipeline of 5 specialized agents searches trusted sources, scrapes and cleans the evidence, cross-references it, checks image authenticity, and returns a verdict with reasoning and citations.

**Constraints:** 100% free stack. Real, usable UI (not just a CLI demo). Buildable in one day by a 5-person team using **Antigravity**. Minimize token usage. Not a chatbot — single-shot verdict tool with an optional lightweight follow-up.

---

## 1. What Makes This "Multi-Agent" (keep this in the pitch)

A multi-agent system = multiple LLM-powered agents, each with:
1. **A distinct role and system prompt** — no agent tries to do another's job.
2. **Distinct tools** — Search agent has web search; Scraper agent has Playwright; Verdict agent has neither, it only reasons over structured input.
3. **Orchestrated handoff** — each agent's output is structured JSON that becomes the next agent's input (see Section 6).
4. **Independent buildability/testability** — each person can build and test their agent against mocked inputs before integration.

DeepFakeLens has 5 such agents in a fixed pipeline order (Section 3) — that's the architecture, and it's also exactly how the team splits (Section 4).

---

## 2. Tech Stack (all free)

| Layer | Choice | Why |
|---|---|---|
| LLM (primary) | **Gemini 2.5 Flash** (Google AI Studio) | Free, ~1,500 req/day, 1M context, multimodal (covers the image path), no card required |
| LLM (fallback) | **Groq — Llama 3.3 70B** | No card, ~30 RPM / ~14,400 req/day, very fast — auto-fallback if Gemini rate-limits mid-demo |
| Search | **Tavily API** (free tier) + **duckduckgo-search** (unlimited, no key) as backup | Finds candidate URLs; DDG is the safety net if Tavily quota runs out during testing |
| Fact-check DB (bonus) | **Google Fact Check Tools API** | Free, structured, credible, no billing needed |
| Web scraping | **Playwright (headless, async)** + **trafilatura** or **readability-lxml** | Renders JS-heavy news pages properly, then strips to clean article text before it ever touches the LLM |
| Image authenticity | **Hugging Face Inference API** (free tier, open AI-image/deepfake detector) + Gemini Vision as a secondary signal | No cost; framed as a signal, not a forensic certification |
| RAG / knowledge cache | **ChromaDB** (in-process, `pip install chromadb`) + **sentence-transformers** (`all-MiniLM-L6-v2`, local) | Free, no server, zero API tokens spent on embeddings — caches past verdicts and holds a pre-seeded knowledge base of known claims |
| Orchestration | **CrewAI** (`pip install crewai`) | Sequential 5-agent pipeline with minimal boilerplate |
| Backend | **FastAPI** | Async, free, auto-docs, easy to wire agents to endpoints |
| Frontend | **React (Vite) + Tailwind** (or plain HTML/JS if time is tight) | Real, usable UI: input form, live per-agent status, verdict card |
| Hosting (optional) | Frontend → Vercel/Netlify free. Backend → Hugging Face Spaces (Docker) or Render free tier | Live demo link instead of localhost |
| Dev environment | **Antigravity** | Delegate each agent as its own task in the Manager surface; use its browser-verification loop to test Playwright scraping live |

---

## 3. Agent Pipeline (5 agents, CrewAI sequential process)

```
User Input (text claim / URL / image)
        │
        ▼
1. INTAKE / CLAIM EXTRACTOR AGENT
   - Normalizes input; detects text vs image
   - For text: extracts the core checkable claim from noisy input
   - For image: calls HF deepfake-detection model (+ Gemini Vision
     as secondary signal) directly — no search needed for this path
   - Rule-based routing where possible (no LLM call needed just to
     check "is this an image upload")
        │
        ▼ (text path only)
1.5. RAG / KNOWLEDGE CHECK
   - Embed the extracted claim locally (sentence-transformers, no API
     call, no tokens spent)
   - Similarity search against ChromaDB (cosine similarity > 0.85 =
     "same claim")
   - MATCH FOUND → return the cached verdict immediately, skip
     Search + Scraper + Analysis entirely (fast + free)
   - NO MATCH → continue to Search Agent as normal
        │
        ▼ (no match only)
2. SEARCH AGENT
   - Tavily / DuckDuckGo query, biased toward trusted domains
     (Reuters, AFP, AAP, Fatabyyano, Misbar, official gov sources)
   - Also queries Google Fact Check Tools API
   - Output: a short list of candidate URLs (capped at 3–4)
        │
        ▼
3. SCRAPER AGENT
   - Opens each candidate URL with Playwright (headless, ~8–10s
     timeout per page, run concurrently with asyncio)
   - Extracts clean article text with trafilatura/readability
     (strips ads/nav/boilerplate)
   - Truncates each source to ~500–800 tokens before handoff
     (biggest single token-saving step in the whole pipeline)
        │
        ▼
4. CROSS-REFERENCE / ANALYSIS AGENT
   - Compares claim against cleaned evidence
   - Flags agreement / contradiction / insufficient evidence per source
   - Weighs credibility using a simple hardcoded trusted-domain tier
     list (no ML scoring — out of scope for one day)
        │
        ▼
5. VERDICT & EXPLAINER AGENT
   - Produces final label: True / False / Misleading / Unverified
   - Writes a short plain-language explanation
   - Lists sources used, each with a link and stance
   - Merges in image-authenticity result if that path was used
        │
        ▼
Write claim + verdict + explanation + sources back into ChromaDB
(so the next similar claim hits the RAG cache instead of re-running
the full pipeline)
        │
        ▼
Returned to UI as structured JSON → rendered as a verdict card
```

---

## 3.5. RAG / Knowledge Layer (cache + curated knowledge base)

Sits right after the Intake Agent, before Search. Serves two purposes at once:

1. **Cache** — any claim the system has already fully verified gets stored, so re-checking the same or a near-identical claim later is instant and free (no search, no scrape, no extra LLM calls).
2. **Curated knowledge base** — pre-seed it with ~20–50 known claims (a mix of well-known true/false claims, including a few Arabic misinformation examples) before the demo, so the system already "knows" some answers on day one.

**How it works:**
- Embed claims **locally** with `sentence-transformers` (`all-MiniLM-L6-v2`) — this costs zero API tokens and zero external calls, unlike using Gemini's embedding endpoint.
- Store embeddings + `{claim, verdict, explanation, sources}` in **ChromaDB** (in-process, no server needed).
- On a new claim: embed it, run a cosine-similarity search against the store.
  - **Similarity > 0.85** → treat as the same claim, return the cached verdict directly, skip Search/Scraper/Analysis entirely.
  - **Below threshold** → treat as new, run the full pipeline, then write the new claim+verdict back into the store for next time.
- Threshold (0.85) is a starting point — tune it during Hour 6.5–7.5 testing; too low causes false cache hits on unrelated claims, too high means the cache rarely fires.

**Why this is legitimate RAG (not just a cache with a fancy name):** it's retrieval (vector similarity search) augmenting generation (the LLM only writes a fresh verdict when retrieval comes back empty) — that's the actual definition, just applied to your own growing claim history plus a pre-seeded set, rather than a static external document corpus.

**Demo value:** guarantees at least one live example can return an instant, zero-API-call result on stage — a strong "look how efficient this is" moment, and a safety net if other live API calls are rate-limited during the demo.

**Owner:** Person B (Search Agent), since it's the first thing checked before web search — see Section 4.

**Files needed for this layer:**

```
rag_store.py       # core logic — owned by Person B
  - init_store()          → creates/loads the ChromaDB collection at startup,
                             loads the sentence-transformers model once
  - check_cache(claim_text) -> dict | None
                             embeds the claim, runs similarity search,
                             returns the cached verdict JSON if similarity > 0.85,
                             else returns None
  - write_to_cache(claim_text, verdict_json) -> None
                             embeds and stores a new verified claim +
                             its verdict after the Verdict Agent finishes

seed_data.json      # the ~20-50 pre-loaded known claims
  [
    {"claim": "...", "verdict": "...", "explanation": "...", "sources": [...]},
    ...
  ]

seed_rag.py          # one-time setup script
  - reads seed_data.json, embeds each claim, loads into ChromaDB
  - run once per environment / once per teammate's machine

chroma_db/            # auto-generated local persistent storage
  - created automatically by ChromaDB when init_store() runs with a
    persist_directory set — not hand-written, add to .gitignore
```

**Integration points (who calls what):**
- `intake_agent.py` (Person A) calls `rag_store.check_cache()` right after extracting the claim.
- `verdict_agent.py` (Person E) calls `rag_store.write_to_cache()` right after producing the final verdict.
- Both `check_cache()` and `write_to_cache()` signatures should be agreed in Hour 1 alongside the JSON contract (Section 6), so Person A and Person E can build against a mocked version (e.g. `check_cache()` returning `None` always) before Person B's real implementation is ready.

---

## 4. Team Split (5 people, 1 agent each)

| Person | Owns | Deliverable |
|---|---|---|
| A | Intake/Claim Extractor Agent + image-authenticity tool call (HF + Gemini Vision) | `/analyze` accepts text or image, routes correctly, returns image verdict directly when applicable |
| B | Search Agent + RAG/Knowledge Cache | Tavily + DuckDuckGo + Fact Check API wired in, returns 3–4 clean candidate URLs biased toward trusted domains. Also: ChromaDB setup, claim embedding + similarity lookup, pre-seeding ~20–50 known claims, write-back after each verdict |
| C | Scraper Agent | Playwright scraping (async, timeout-guarded) + trafilatura cleanup + token-capped output per source |
| D | Cross-Reference / Analysis Agent | Evidence → per-source stance + credibility-weighted summary as structured JSON |
| E | Verdict/Explainer Agent + FastAPI backend wiring + Frontend UI | Final label + explanation + sources; end-to-end app connecting all 5 agents to a working UI |

Each person builds and tests their agent independently against mocked inputs/outputs first (using the JSON contract in Section 6), then the team integrates in the afternoon.

---

## 5. Timeline (1 day, ~8 hours)

| Time | Task |
|---|---|
| Hour 1 | Repo setup, get all free API keys, lock the JSON contract (Section 6), install CrewAI/FastAPI/Playwright (`playwright install`) |
| Hour 2–4 | Each person builds/tests their agent in isolation in Antigravity, against mocked inputs from the contract |
| Hour 4–5 | Integrate all 5 agents into one CrewAI sequential pipeline behind a single FastAPI endpoint |
| Hour 5–6.5 | Build the frontend: input form (text/URL/image), live per-agent status trail, verdict card + sources display |
| Hour 6.5–7.5 | End-to-end testing with real claims, incl. at least one Arabic-language claim and one AI-generated image; fix integration bugs |
| Hour 7.5–8 | Polish UI, prep 2–3 rehearsed demo examples (with screenshot backups), deploy live link if time allows |

---

## 6. Shared JSON Contract (lock this in Hour 1)

```json
// Input to pipeline
{
  "input_type": "text" | "image",
  "text_claim": "string or null",
  "image_url": "string or null",
  "language": "ar" | "en"
}

// RAG / Knowledge Check output (after Intake, before Search)
{
  "cache_hit": true,
  "cached_verdict": { /* same shape as final pipeline output below */ } // null if no match
}

// Search Agent output → Scraper Agent input (only runs if cache_hit is false)
{
  "candidate_urls": ["string", "..."]
}

// Scraper Agent output → Analysis Agent input
{
  "sources": [
    {"url": "string", "title": "string", "clean_text": "string (truncated ~500-800 tokens)"}
  ]
}

// Analysis Agent output → Verdict Agent input
{
  "per_source": [
    {"url": "string", "stance": "supports" | "contradicts" | "context", "credibility_tier": "high" | "medium" | "low"}
  ]
}

// Final pipeline output → Frontend
{
  "verdict": "true" | "false" | "misleading" | "unverified",
  "confidence": 0.0,
  "explanation": "string",
  "sources": [
    {"title": "string", "url": "string", "stance": "supports" | "contradicts" | "context"}
  ],
  "image_authenticity": {
    "is_ai_generated": true,
    "confidence": 0.0,
    "note": "string"
  } // null if input_type was text
}
```

Locking this early means all 5 people build against mocks in parallel, and integration in Hour 4 is plumbing, not redesign.

---

## 7. User Flow (first-time use)

1. Land on a single page: text input box + "or upload an image" toggle. Optional language selector (auto-detect Arabic/English by default).
2. Submit a claim or an image → click "Check."
3. UI shows a **live status trail** as agents run ("Searching sources…", "Reading articles…", "Cross-referencing…", "Writing verdict…") — builds trust and doubles as a demo beat.
4. Result: a verdict card with label, plain-language explanation, and clickable sources. Image path shows an authenticity readout with an explicit "signal, not certified forensic result" caveat.
5. "Check another claim" resets state. No login, no history — stateless by design.

**Interaction model:** single-shot submit → verdict, not a chatbot. Optionally add one lightweight "Ask a follow-up" input under the verdict card — it reuses the evidence already gathered (no new search/scrape, just one more cheap LLM call on cached context) rather than building a full multi-turn chat interface.

---

## 8. Token-Minimization Checklist

- Never send raw HTML to an LLM — always scrape → clean (trafilatura) → truncate (~500–800 tokens/source) first.
- Use Gemini **Flash**, not Pro, everywhere (Pro's free-tier cap is far too low to build against).
- Cap sources at 3–4 per claim, not 10.
- Keep all 5 agents as separate, real LLM calls (don't merge steps) — the token cost of doing so is small next to scraping, and merging would weaken the "5 real agents" architecture claim.
- Cache scrape results and verdicts in memory during testing so repeated test runs on the same claim don't re-burn quota.
- Routing decisions (text vs image) are `if` statements, not LLM calls.
- RAG cache hits skip Search + Scraper + Analysis entirely — the single biggest token/time saver available whenever a claim repeats.
- Embeddings for the RAG layer run **locally** (sentence-transformers) — never call a paid/rate-limited embedding API for this.

---

## 9. Scope Guardrails (say no to these today)

- No ML-based credibility scoring — hardcoded trusted-domain tier list only.
- No fine-tuned deepfake detector — use an existing free HF model as-is, with an explicit "signal, not certified" caveat in the UI.
- No user accounts, history, or database — stateless, one request in, one verdict out.
- No broad rumor/narrative verification — scope to specific, checkable claims (a stat, a quote, "did X happen").
- No full multi-turn chatbot — single-shot verdict + optional single follow-up only.

---

## 10. Building This in Antigravity

- Use the **Manager Surface** to spawn one task per agent (5 tasks) so agents can be built somewhat in parallel across the team, each in its own workspace.
- For the **Scraper Agent** specifically, lean into Antigravity's browser-control loop: let the agent open real target URLs, verify the extracted text looks right, and self-correct selectors/timeouts — this is exactly the autonomous "code → run in browser → verify" pattern Antigravity is built for.
- Use the **Walkthrough** artifact after each agent task to quickly sanity-check what changed before merging into the integrated pipeline.
- Keep the Editor view for the FastAPI/frontend integration work in Hour 4–6, where you want tighter manual control.

---

## 11. Demo Script (prepare in advance)

1. A **false** claim with a clear correction (ideally Arabic, ideally recognizable) — the core value prop.
2. A **true** claim — shows the system isn't biased toward "false."
3. An **AI-generated image** — shows the multimodal feature working.

Have screenshot backups of successful runs in case live API calls hit a rate limit during the actual demo.

---

## 12. Environment Variables Needed

```
GEMINI_API_KEY=
GROQ_API_KEY=
TAVILY_API_KEY=
GOOGLE_FACTCHECK_API_KEY=
HF_API_TOKEN=
```

All free, no card required, obtainable in under 10 minutes total.

---

## 13. Next Steps

- [ ] Each of the 5 team members gets their free API keys (Hour 1)
- [ ] Lock the JSON contract in Section 6
- [ ] `pip install crewai fastapi playwright trafilatura chromadb sentence-transformers` + `playwright install`
- [ ] Set up repo with clear module boundaries (one file/folder per agent)
- [ ] Prepare the ~20–50 claim seed list for the RAG knowledge base (mix of true/false, include Arabic examples)
- [ ] Spawn 5 tasks in Antigravity's Manager surface, one per agent, and start building in parallel
