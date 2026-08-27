"""
Strict JSON contract tests against DeepFakeLens specification (imp.md Section 6).
"""

import json
from pydantic import BaseModel, ValidationError
from typing import List, Literal, Optional

import verdict_agent
import pipeline


class StrictSourceContract(BaseModel):
    title: str
    url: str
    stance: Literal["supports", "contradicts", "context"]


class StrictImageAuthenticityContract(BaseModel):
    is_ai_generated: bool
    confidence: float
    note: str


class StrictFinalPipelineOutputContract(BaseModel):
    verdict: Literal["true", "false", "misleading", "unverified"]
    confidence: float
    explanation: str
    sources: List[StrictSourceContract]
    image_authenticity: Optional[StrictImageAuthenticityContract] = None


def test_contract_compliance_verdict_agent():
    with open("mock_input.json", "r", encoding="utf-8") as f:
        mock_data = json.load(f)

    result = verdict_agent.generate_verdict(
        claim=mock_data["claim"],
        per_source=mock_data["per_source"],
        image_authenticity=mock_data.get("image_authenticity"),
        language=mock_data.get("language", "en"),
        write_to_rag=False
    )

    # Validates without throwing ValidationError
    validated = StrictFinalPipelineOutputContract(**result)
    assert validated.verdict in ("true", "false", "misleading", "unverified")
    assert 0.0 <= validated.confidence <= 1.0
    assert validated.image_authenticity is None


def test_contract_compliance_image_pipeline():
    with open("mock_input_image.json", "r", encoding="utf-8") as f:
        mock_data = json.load(f)

    result = pipeline.run_pipeline(
        input_type="image",
        text_claim=mock_data["claim"],
        image_url="https://example.com/squid.png",
        language="en"
    )

    validated = StrictFinalPipelineOutputContract(**result)
    assert validated.image_authenticity is not None
    assert isinstance(validated.image_authenticity.is_ai_generated, bool)
    assert 0.0 <= validated.image_authenticity.confidence <= 1.0
