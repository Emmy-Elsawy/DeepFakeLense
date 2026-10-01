# 🔍 DeepFakeLens — Multi-Agent AI Fact-Checking Backend

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

DeepFakeLens is an autonomous 5-agent AI fact-checking and deepfake verification pipeline designed for real-time claim investigation. Built on a 100% free stack (Gemini 2.5 Flash, Groq Llama 3.3 70B, Tavily/DuckDuckGo, ChromaDB RAG cache, and FastAPI).

This repository contains **Agent 5 (`verdict_agent.py`)** and the **FastAPI REST backend (`main.py`)** wired with modular agent stubs, full CORS support for Google Stitch frontends, and automated OpenAPI documentation.

---

## 🏗️ 5-Agent Architecture

```
User Input (Text Claim or Image URL)
               │
               ▼
   [1. Intake / Claim Extractor Agent] (Person A)
         │                         │ (Image Path)
         ▼ (Text Path)             ▼
 [1.5. RAG Vector Cache Check]   [HF Deepfake Detector + Gemini Vision]
   (ChromaDB / all-MiniLM-L6-v2)           │
         │ (Cache Hit > 0.85)              │
         ├───────────────────────┐         │
         │ (Cache Miss)          │         │
         ▼                       │         │
   [2. Search Agent] (Person B)  │         │
         │                       │         │
         ▼                       │         │
   [3. Scraper Agent] (Person C) │         │
         │                       │         │
         ▼                       │         │
   [4. Analysis Agent] (Person D)│         │
         │                       │         │
         ▼                       │         │
   [5. Verdict Agent] (Person E) │         │
         │                       │         │
         ├───────────────────────┼─────────┘
         │ (Write to Cache)      │
         ▼                       ▼
   [Final Output JSON -> Google Stitch UI]
```

---

## 📦 Deliverables & File Structure

| File | Purpose | Owner |
|---|---|---|
| `verdict_agent.py` | Verdict & Explainer Agent (Gemini 2.5 Flash + Groq fallback + RAG write-back) | **Person E** |
| `main.py` | FastAPI application with `/analyze`, `/follow-up`, `/health`, CORS, and `/docs` | **Person E** |
| `pipeline.py` | 5-agent sequential orchestrator & modular teammate stubs | **Person E** |
| `rag_store.py` | ChromaDB vector cache interface (`check_cache`, `write_to_cache`) | **Person B** / Stub |
| `mock_input.json` | Locked schema input for standalone agent testing | Contract |
| `mock_input_image.json` | Multimodal mock input for image authenticity verification | Contract |
| `tests/` | Complete automated pytest suite (15 unit/integration/contract tests) | **Person E** |
| `Dockerfile` | Production container for Render and Hugging Face Spaces | **Person E** |
| `requirements.txt` | Pinned backend and agent dependencies | **Person E** |

---

## 🚀 Quick Start (Local Development)

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/<your-username>/DeepFakeLens.git
cd DeepFakeLens

python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and insert your free API keys:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_from_google_ai_studio
GROQ_API_KEY=your_groq_api_key_from_groq_console
PORT=8000
CORS_ORIGINS=*
```
*(Note: If no API keys are provided, the system automatically runs in deterministic local fallback mode for offline testing).*

### 3. Run Standalone Verdict Agent
```bash
python verdict_agent.py mock_input.json
```

### 4. Start FastAPI Backend
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI Docs: `http://localhost:8000/docs`
- OpenAPI JSON Spec: `http://localhost:8000/openapi.json`
- Health Check: `http://localhost:8000/health`

### 5. Run Automated Tests
```bash
pytest -v
```

---

## 📡 REST API Specification

### 1. `POST /analyze`
Primary pipeline endpoint. Accepts a claim or image URL and orchestrates the full 5-agent verification.

#### Request Body:
```json
{
  "input_type": "text",
  "text_claim": "UNESCO declared the Great Wall of China as the only man-made structure visible from the Moon.",
  "image_url": null,
  "language": "en"
}
```

#### Response (Locked JSON Contract):
```json
{
  "verdict": "false",
  "confidence": 0.95,
  "explanation": "The claim is false. Verified records and astronaut observations confirm the Great Wall is not visible from the Moon with the naked eye.",
  "sources": [
    {
      "title": "NASA - China's Wall Less Great in View from Space",
      "url": "https://www.nasa.gov/vision/space/workinginspace/great_wall.html",
      "stance": "contradicts"
    },
    {
      "title": "Scientific American - Is China's Great Wall Visible from Space?",
      "url": "https://www.scientificamerican.com/article/is-chinas-great-wall-visible-space/",
      "stance": "contradicts"
    }
  ],
  "image_authenticity": null
}
```

---

### 2. `POST /follow-up`
Reuses context from a previous verdict to answer user follow-ups without re-scraping or re-searching.

#### Request Body:
```json
{
  "question": "Can it be seen from low Earth orbit instead?",
  "context": {
    "verdict": "false",
    "explanation": "Astronauts confirm the Great Wall cannot be seen from space without optical aid.",
    "sources": [
      {"title": "NASA", "url": "https://nasa.gov", "stance": "contradicts"}
    ]
  },
  "language": "en"
}
```

#### Response:
```json
{
  "answer": "According to NASA, even in low Earth orbit, the Great Wall is barely visible under perfect atmospheric conditions and only with high-powered camera lenses, but not distinctly with the naked human eye."
}
```

---

## 🌐 Google Stitch Frontend Integration Guide

The backend is pre-configured with CORS (`Access-Control-Allow-Origin: *`), allowing direct browser `fetch()` calls from Google Stitch web apps.

### JavaScript Integration Example:
```javascript
const API_BASE_URL = "https://your-deployment-url.onrender.com"; // or http://localhost:8000

// 1. Submit Claim for Verification
async function verifyClaim(textClaim, language = "en") {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      input_type: "text",
      text_claim: textClaim,
      language: language
    })
  });
  const data = await response.json();
  console.log("Verdict:", data.verdict);
  console.log("Confidence:", data.confidence);
  console.log("Explanation:", data.explanation);
  return data;
}

// 2. Ask Follow-up Question
async function askFollowUp(question, priorVerdictObject, language = "en") {
  const response = await fetch(`${API_BASE_URL}/follow-up`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question: question,
      context: priorVerdictObject,
      language: language
    })
  });
  const result = await response.json();
  console.log("Answer:", result.answer);
  return result.answer;
}
```

---

## ☁️ Deployment Instructions

### Option A: Deploy to Render (Recommended Free Web Service)

1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "feat: DeepFakeLens verdict agent and FastAPI backend"
   git branch -M main
   git remote add origin https://github.com/<your-username>/DeepFakeLens.git
   git push -u origin main
   ```

2. **Create Web Service on Render**:
   - Go to [dashboard.render.com](https://dashboard.render.com/) and click **New + > Web Service**.
   - Connect your GitHub repository `DeepFakeLens`.
   - **Environment**: Select `Docker` (or `Python 3`).
   - **Build Command**: (Automatically uses `Dockerfile` or `pip install -r requirements.txt`).
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Select **Free**.

3. **Add Environment Variables in Render**:
   - `GEMINI_API_KEY`: `<Your-Gemini-API-Key>`
   - `GROQ_API_KEY`: `<Your-Groq-API-Key>`
   - `CORS_ORIGINS`: `*`

4. **Deploy**:
   - Click **Create Web Service**.
   - Render will build the container and provide your live URL (e.g. `https://deepfakelens.onrender.com`).
   - Test by opening `https://deepfakelens.onrender.com/docs`.

---

### Option B: Deploy to Hugging Face Spaces (Docker Space)

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. **Space Name**: `DeepFakeLens`
3. **SDK**: Select **Docker** (Blank).
4. **Visibility**: Public.
5. In **Space Settings > Variables and secrets**, add:
   - Secret `GEMINI_API_KEY`
   - Secret `GROQ_API_KEY`
6. Push the repo to Hugging Face Spaces git remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/DeepFakeLens
   git push space main
   ```
7. Hugging Face Spaces will build the `Dockerfile` and expose port `7860`. The API and `/docs` will be live immediately.

---

## 🧩 Teammate Integration Guide

As teammates deliver real implementations for Agents 1-4 and the RAG store:
1. **Agent 1 (Person A)**: Place `intake_agent.py` in root and replace `run_intake_agent` / `run_image_authenticity_check` in `pipeline.py`.
2. **Agent 2 (Person B)**: Place `search_agent.py` in root and replace `run_search_agent` in `pipeline.py`.
3. **Agent 3 (Person C)**: Place `scraper_agent.py` in root and replace `run_scraper_agent` in `pipeline.py`.
4. **Agent 4 (Person D)**: Place `analysis_agent.py` in root and replace `run_analysis_agent` in `pipeline.py`.
5. **RAG Store (Person B)**: Replace `rag_store.py` with full ChromaDB persistent implementation if desired (the interface signatures `check_cache` and `write_to_cache` are already 100% matched).
