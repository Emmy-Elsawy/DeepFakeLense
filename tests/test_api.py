"""
Integration tests for FastAPI endpoints (main.py).
"""

import pytest
from fastapi.testclient import TestClient

from main import app
import rag_store

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_store():
    rag_store.init_store()


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "docs_url" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "DeepFakeLens Backend"


def test_analyze_text_claim():
    payload = {
        "input_type": "text",
        "text_claim": "The Great Wall of China is the only man-made structure visible from the Moon with the naked eye.",
        "language": "en"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["verdict"] in ("true", "false", "misleading", "unverified")
    assert isinstance(data["confidence"], float)
    assert isinstance(data["explanation"], str)
    assert isinstance(data["sources"], list)
    assert data["image_authenticity"] is None


def test_analyze_image_claim():
    payload = {
        "input_type": "image",
        "image_url": "https://example.com/test_ai_image.png",
        "text_claim": "Giant sea creature photograph",
        "language": "en"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["verdict"] in ("true", "false", "misleading", "unverified")
    assert data["image_authenticity"] is not None
    assert "is_ai_generated" in data["image_authenticity"]
    assert "confidence" in data["image_authenticity"]
    assert "note" in data["image_authenticity"]


def test_analyze_validation_errors():
    # Missing text_claim when input_type is text
    response = client.post("/analyze", json={"input_type": "text"})
    assert response.status_code == 422

    # Invalid input_type
    response = client.post("/analyze", json={"input_type": "audio"})
    assert response.status_code == 422


def test_follow_up_endpoint():
    context = {
        "verdict": "false",
        "confidence": 0.95,
        "explanation": "NASA confirmed the Great Wall of China is not visible from space without magnification.",
        "sources": [
            {"title": "NASA", "url": "https://nasa.gov", "stance": "contradicts"}
        ],
        "image_authenticity": None
    }
    payload = {
        "question": "Can you see it from low Earth orbit instead?",
        "context": context,
        "language": "en"
    }
    response = client.post("/follow-up", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_cors_headers():
    # Test pre-flight OPTIONS request
    headers = {
        "Origin": "https://stitch.google.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    }
    response = client.options("/analyze", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://stitch.google.com" or response.headers.get("access-control-allow-origin") == "*"

    # Test standard GET request CORS
    res_get = client.get("/health", headers={"Origin": "https://stitch.google.com"})
    assert res_get.headers.get("access-control-allow-origin") in ("https://stitch.google.com", "*")
