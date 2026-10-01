"""
Tests for Intake / Claim Extractor Agent (intake_agent.py).
"""

from __future__ import annotations
import json
import pytest
from unittest.mock import patch, MagicMock

import intake_agent
import rag_store


@pytest.fixture(autouse=True)
def reset_rag_cache():
    rag_store.init_store()


def test_intake_routing_and_contract_validation():
    # Invalid input type should raise ValueError
    with pytest.raises(ValueError, match="Invalid input_type"):
        intake_agent.run_intake(input_type="audio", text_claim="Some claim")

    # Missing text_claim on text path should raise ValueError
    with pytest.raises(ValueError, match="text_claim is required"):
        intake_agent.run_intake(input_type="text", text_claim=None)

    # Missing image_url on image path should raise ValueError
    with pytest.raises(ValueError, match="image_url is required"):
        intake_agent.run_intake(input_type="image", image_url=None)


def test_intake_text_path_local_fallback():
    # Test text path when no API keys are present (local fallback)
    with patch.dict("os.environ", {}, clear=True):
        result = intake_agent.run_intake(
            input_type="text",
            text_claim="I honestly think that NASA finally confirmed that the Great Wall of China is visible from the Moon with the naked eye! That's what I read yesterday.",
            language="en"
        )
        assert result["input_type"] == "text"
        assert "Great Wall of China" in result["extracted_claim"]
        assert result["image_url"] is None
        assert result["language"] == "en"


def test_intake_text_path_arabic_local_fallback():
    # Test Arabic claim language detection / confirmation locally
    with patch.dict("os.environ", {}, clear=True):
        result = intake_agent.run_intake(
            input_type="text",
            text_claim="سمعت خبر إن منظمة اليونسكو أعلنت رسمياً إن سور الصين العظيم هو المعلم الوحيد من صنع الإنسان",
            language="ar"
        )
        assert result["input_type"] == "text"
        assert result["language"] == "ar"
        assert "اليونسكو" in result["extracted_claim"]


def test_intake_text_path_gemini_success():
    mock_llm_output = {
        "extracted_claim": "The Great Wall of China is visible from the Moon.",
        "language": "en"
    }

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_gemini_key"}):
        with patch("intake_agent._call_gemini_text", return_value=mock_llm_output) as mock_gemini:
            result = intake_agent.run_intake(
                input_type="text",
                text_claim="Is it true that the Great Wall of China is visible from the Moon?",
                language="en"
            )
            mock_gemini.assert_called_once()
            assert result["extracted_claim"] == "The Great Wall of China is visible from the Moon."
            assert result["language"] == "en"


def test_intake_text_path_groq_fallback():
    mock_llm_output = {
        "extracted_claim": "The Great Wall of China is visible from the Moon.",
        "language": "en"
    }

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_gemini_key", "GROQ_API_KEY": "fake_groq_key"}):
        # Gemini fails, should fall back to Groq
        with patch("intake_agent._call_gemini_text", side_effect=Exception("Rate Limit")):
            with patch("intake_agent._call_groq_text", return_value=mock_llm_output) as mock_groq:
                result = intake_agent.run_intake(
                    input_type="text",
                    text_claim="Is it true that the Great Wall of China is visible from the Moon?",
                    language="en"
                )
                mock_groq.assert_called_once()
                assert result["extracted_claim"] == "The Great Wall of China is visible from the Moon."
                assert result["language"] == "en"


def test_intake_image_path_local_fallback():
    # When APIs are not set, it should fall back to local rule-based mock for image path
    with patch.dict("os.environ", {}, clear=True):
        result = intake_agent.run_intake(
            input_type="image",
            image_url="https://example.com/viral_squid.png",
            text_claim="Viral photo of a giant glowing squid",
            language="en"
        )
        assert result["verdict"] == "false"
        assert result["confidence"] == 0.94
        assert result["image_authenticity"]["is_ai_generated"] is True
        assert "Offline local detector" in result["image_authenticity"]["note"]
        assert result["sources"] == []


def test_intake_image_path_signal_combining():
    mock_hf_output = {
        "is_ai_generated": True,
        "confidence": 0.90
    }
    mock_gemini_output = {
        "is_ai_generated": True,
        "confidence": 0.94,
        "note": "Midjourney style artifacts detected in lighting."
    }

    # Simulate downloading/reading image bytes successfully
    with patch("intake_agent.httpx.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"fake_image_bytes", headers={"content-type": "image/png"})
        
        # Patch both calls to return mock signals
        with patch("intake_agent._call_hf_image_detector", return_value=mock_hf_output) as mock_hf:
            with patch("intake_agent._call_gemini_vision", return_value=mock_gemini_output) as mock_gemini:
                with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key", "HF_API_TOKEN": "fake_token"}):
                    result = intake_agent.run_intake(
                        input_type="image",
                        image_url="https://example.com/any_image.png",
                        text_claim="Some image to test",
                        language="en"
                    )
                    mock_hf.assert_called_once()
                    mock_gemini.assert_called_once()
                    
                    assert result["verdict"] == "false"
                    assert result["confidence"] == 0.92  # Average of 0.90 and 0.94
                    assert result["image_authenticity"]["is_ai_generated"] is True
                    assert "HF Signal" in result["image_authenticity"]["note"]
                    assert "Midjourney style artifacts" in result["image_authenticity"]["note"]
