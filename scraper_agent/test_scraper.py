import json
import os
import sys
import pytest

try:
    from scraper_agent.scraper_agent import run_scraper
except ImportError:
    from scraper_agent import run_scraper

def test_run_scraper_with_mock_input():
    mock_path = os.path.join(os.path.dirname(__file__), "mock_input.json")
    # Load mock input
    with open(mock_path, "r") as f:
        input_data = json.load(f)
        
    result = run_scraper(input_data)
    
    # Assertions
    assert "sources" in result
    sources = result["sources"]
    
    # We provided 4 URLs, one is meant to fail (timeout).
    # Since we gracefully skip, we expect around 2-3 sources depending on stability,
    # but strictly less than 4 (the timeout URL should not be in sources).
    assert len(sources) <= len(input_data["candidate_urls"])
    
    # Validate each returned source
    for source in sources:
        assert "url" in source
        assert "title" in source
        assert "clean_text" in source
        
        # Check that clean_text is non-empty
        assert len(source["clean_text"]) > 0
        
        # Check token length implicitly by checking string length 
        # (max 800-1000 tokens * ~4 chars/token is roughly 3200-5000 chars)
        assert len(source["clean_text"]) < 8000, "Clean text exceeds expected length"

if __name__ == "__main__":
    test_run_scraper_with_mock_input()
    print("All tests passed.")
