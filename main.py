"""
DeepFakeLens — FastAPI Backend API

Features:
  - POST /analyze: Primary fact-checking endpoint orchestrating the 5-agent pipeline.
  - POST /follow-up: Single-shot LLM follow-up answering using prior verdict context.
  - GET /health: Health check endpoint for uptime monitoring.
  - GET /: Welcome route with API metadata & docs link.
  - Full CORS support for Google Stitch browser-based clients.
  - Auto-generated OpenAPI / Swagger documentation (/docs).
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Literal, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import pipeline
import rag_store

load_dotenv()


# ============================================================================
# Pydantic Request & Response Models (Locked JSON Contract)
# ============================================================================

class SourceItem(BaseModel):
    title: str = Field(
        ...,
        description="Headline or title of the cited evidence source.",
        examples=["NASA - China's Wall Less Great in View from Space"]
    )
    url: str = Field(
        ...,
        description="Canonical URL of the source article or fact check.",
        examples=["https://www.nasa.gov/vision/space/workinginspace/great_wall.html"]
    )
    stance: Literal["supports", "contradicts", "context"] = Field(
        ...,
        description="The source's stance towards the claim.",
        examples=["contradicts"]
    )


class ImageAuthenticityItem(BaseModel):
    is_ai_generated: bool = Field(
        ...,
        description="Whether forensic signals indicate the image was generated or manipulated by AI.",
        examples=[True]
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection confidence score from 0.0 to 1.0.",
        examples=[0.94]
    )
    note: str = Field(
        ...,
        description="Forensic observation notes and model signal breakdown.",
        examples=["Synthesized artifacts and lighting inconsistencies detected."]
    )


class AnalyzeRequest(BaseModel):
    input_type: Literal["text", "image"] = Field(
        ...,
        description="Type of verification input: 'text' for textual claims or 'image' for image checks.",
        examples=["text"]
    )
    text_claim: Optional[str] = Field(
        default=None,
        description="Textual claim or statement to fact check (required if input_type is 'text').",
        examples=["UNESCO declared the Great Wall of China as the only man-made structure visible from the Moon."]
    )
    image_url: Optional[str] = Field(
        default=None,
        description="Public URL to the image to analyze (required if input_type is 'image').",
        examples=["https://example.com/viral_image.jpg"]
    )
    language: Optional[Literal["en", "ar"]] = Field(
        default="en",
        description="Target output language for explanations ('en' for English, 'ar' for Arabic).",
        examples=["en"]
    )


class PipelineResponse(BaseModel):
    verdict: Literal["true", "false", "misleading", "unverified"] = Field(
        ...,
        description="Definitive fact-checking verdict category.",
        examples=["false"]
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score in the verdict from 0.0 to 1.0.",
        examples=[0.95]
    )
    explanation: str = Field(
        ...,
        description="Clear, plain-language summary for non-experts detailing the reasoning.",
        examples=["The claim is false. Verified records and astronaut observations confirm the wall is not visible from the Moon with the naked eye."]
    )
    sources: List[SourceItem] = Field(
        default_factory=list,
        description="List of cited evidence sources with URLs and stances."
    )
    image_authenticity: Optional[ImageAuthenticityItem] = Field(
        default=None,
        description="Image authenticity detection details (null if input was text only)."
    )


class FollowUpRequest(BaseModel):
    question: str = Field(
        ...,
        description="Follow-up question about the fact-check result.",
        examples=["Why did people think it was visible from the Moon in the first place?"]
    )
    context: Dict[str, Any] = Field(
        ...,
        description="The prior verdict object (PipelineResponse) providing cached evidence context."
    )
    language: Optional[Literal["en", "ar"]] = Field(
        default="en",
        description="Language for the follow-up response.",
        examples=["en"]
    )


class FollowUpResponse(BaseModel):
    answer: str = Field(
        ...,
        description="Concise answer directly addressing the follow-up question using cached evidence.",
        examples=["The myth predates spaceflight and was popularized in 1938 by Richard Halliburton's travel book before human space missions debunked it."]
    )


class HealthResponse(BaseModel):
    status: str = Field(default="ok", examples=["ok"])
    service: str = Field(default="DeepFakeLens Backend", examples=["DeepFakeLens Backend"])
    version: str = Field(default="1.0.0", examples=["1.0.0"])


# ============================================================================
# FastAPI Lifespan & Application Setup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize RAG store / ChromaDB collection on startup
    rag_store.init_store()
    yield


app = FastAPI(
    title="DeepFakeLens API",
    description=(
        "5-Agent Fact-Checking & Deepfake Detection Pipeline API.\n\n"
        "Free Stack Architecture: Gemini 2.5 Flash, Groq Llama 3.3 70B, Tavily/DuckDuckGo, "
        "ChromaDB RAG, and FastAPI.\n\n"
        "Designed to be consumed directly by Google Stitch frontends."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Google Stitch browser requests
cors_origins_env = os.environ.get("CORS_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Routes
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
    """Root endpoint providing service metadata and links."""
    return {
        "name": "DeepFakeLens API",
        "status": "running",
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "description": "5-Agent AI Fact-Checking Pipeline Backend"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for Docker / Render / Hugging Face Spaces."""
    return HealthResponse(status="ok", service="DeepFakeLens Backend", version="1.0.0")


@app.post(
    "/analyze",
    response_model=PipelineResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
    summary="Run full 5-agent fact checking pipeline"
)
async def analyze_claim(request: AnalyzeRequest):
    """
    Executes the complete DeepFakeLens pipeline:
    1. **Intake**: Normalizes input and validates claim/image.
    2. **RAG Cache**: Checks local ChromaDB cache. If hit (>0.85 similarity), returns instantly.
    3. **Search & Scrape**: Queries trusted sources and extracts clean article text (if cache miss).
    4. **Cross-Reference**: Evaluates source stances and credibility tiers.
    5. **Verdict**: Synthesizes final verdict via Gemini 2.5 Flash (Groq fallback), caches result, and returns JSON.
    """
    if request.input_type == "text" and not request.text_claim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'text_claim' is required when input_type is 'text'."
        )

    if request.input_type == "image" and not request.image_url and not request.text_claim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'image_url' or 'text_claim' is required when input_type is 'image'."
        )

    try:
        result = pipeline.run_pipeline(
            input_type=request.input_type,
            text_claim=request.text_claim,
            image_url=request.image_url,
            language=request.language or "en"
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline processing failed: {str(e)}"
        )


@app.post(
    "/follow-up",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
    summary="Ask a follow-up question on prior verdict"
)
async def follow_up_question(request: FollowUpRequest):
    """
    Performs a single lightweight LLM call to answer a follow-up question reusing
    cached context from the previous verdict. No re-searching or re-scraping.
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'question' cannot be empty."
        )

    try:
        result = pipeline.answer_follow_up(
            question=request.question,
            context=request.context,
            language=request.language or "en"
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Follow-up answering failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
