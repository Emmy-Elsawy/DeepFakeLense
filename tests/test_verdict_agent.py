"""
Tests for Verdict & Explainer Agent (verdict_agent.py).
"""

import json
import pytest
from unittest.mock import patch, MagicMock

import verdict_agent
import rag_store


@pytest.fixture(autouse=True)
def reset_rag_cache():
    rag_store.init_store()


def test_verdict_agent_with_mock_input():
    with open("mock_input.json", "r", encoding="utf-8") as f:
        mock_data = json.load(f)

    result = verdict_agent.generate_verdict(
        claim=mock_data["claim"],
        per_source=mock_data["per_source"],
        image_authenticity=mock_data.get("image_authenticity"),
        language=mock_data.get("language", "en")
    )

    assert result["verdict"] in ("true", "false", "misleading", "unverified")
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["explanation"], str) and len(result["explanation"]) > 0
    assert isinstance(result["sources"], list)
    assert len(result["sources"]) == 3
    for s in result["sources"]:
        assert "title" in s
        assert "url" in s
        assert s["stance"] in ("supports", "contradicts", "context")
    assert result["image_authenticity"] is None


def test_verdict_agent_with_image_input():
    with open("mock_input_image.json", "r", encoding="utf-8") as f:
        mock_data = json.load(f)

    result = verdict_agent.generate_verdict(
        claim=mock_data["claim"],
        per_source=mock_data["per_source"],
        image_authenticity=mock_data.get("image_authenticity"),
        language=mock_data.get("language", "en")
    )

    assert result["verdict"] == "false"
    assert result["confidence"] >= 0.85
    assert result["image_authenticity"] is not None
    assert result["image_authenticity"]["is_ai_generated"] is True
    assert result["image_authenticity"]["confidence"] == 0.94


def test_verdict_agent_arabic_language():
    result = verdict_agent.generate_verdict(
        claim="ادعاء باللغة العربية للاختبار",
        per_source=[
            {"url": "https://fatabyyano.net/debunk-1", "title": "فتبينوا", "stance": "contradicts", "credibility_tier": "high"}
        ],
        language="ar"
    )

    assert result["verdict"] == "false"
    assert len(result["explanation"]) > 0
    assert result["sources"][0]["url"] == "https://fatabyyano.net/debunk-1"


def test_verdict_agent_writes_to_rag_cache():
    test_claim = "Specific test claim for cache verification 12345"
    result = verdict_agent.generate_verdict(
        claim=test_claim,
        per_source=[{"url": "https://example.com", "stance": "supports", "credibility_tier": "high"}],
        write_to_rag=True
    )

    cached_verdict = rag_store.check_cache(test_claim, similarity_threshold=0.85)
    assert cached_verdict is not None
    assert cached_verdict["verdict"] == result["verdict"]


def test_verdict_agent_gemini_path_success():
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "verdict": "true",
        "confidence": 0.96,
        "explanation": "Verified by NASA press releases.",
        "sources": [{"title": "NASA", "url": "https://nasa.gov", "stance": "supports"}]
    })

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_gemini_key"}):
        with patch("verdict_agent._call_gemini", return_value=json.loads(mock_response.text)) as mock_gemini:
            result = verdict_agent.generate_verdict(
                claim="Water ice exists on the Moon",
                per_source=[{"url": "https://nasa.gov", "title": "NASA", "stance": "supports", "credibility_tier": "high"}]
            )
            mock_gemini.assert_called_once()
            assert result["verdict"] == "true"
            assert result["confidence"] == 0.96


def test_verdict_agent_groq_fallback_when_gemini_fails():
    mock_groq_data = {
        "verdict": "misleading",
        "confidence": 0.80,
        "explanation": "Partially verified context.",
        "sources": [{"title": "Fact Check", "url": "https://factcheck.org", "stance": "context"}]
    }

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key", "GROQ_API_KEY": "fake_groq_key"}):
        with patch("verdict_agent._call_gemini", side_effect=Exception("Gemini Rate Limit Exceeded")):
            with patch("verdict_agent._call_groq", return_value=mock_groq_data) as mock_groq:
                result = verdict_agent.generate_verdict(
                    claim="Some mixed claim",
                    per_source=[{"url": "https://factcheck.org", "title": "Fact Check", "stance": "context", "credibility_tier": "high"}]
                )
                mock_groq.assert_called_once()
                assert result["verdict"] == "misleading"
                assert result["confidence"] == 0.80
