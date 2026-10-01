"""
Unit & Integration Tests for DeepFakeLens Analysis Agent
File: test_analysis_agent.py
"""

import json
import os
import unittest
from analysis_agent import (
    AnalysisAgent,
    extract_domain,
    get_credibility_tier,
    _deterministic_heuristic_fallback,
    run_analysis,
)


class TestDomainCredibilityTier(unittest.TestCase):
    """Test the hardcoded credibility tier classification."""

    def test_extract_domain(self):
        self.assertEqual(extract_domain("https://www.reuters.com/world"), "reuters.com")
        self.assertEqual(extract_domain("http://news.bbc.co.uk/articles/123"), "news.bbc.co.uk")
        self.assertEqual(extract_domain("techcrunch.com/article"), "techcrunch.com")
        self.assertEqual(extract_domain("https://sub.defense.gov/report"), "sub.defense.gov")

    def test_high_credibility_domains(self):
        high_urls = [
            "https://www.reuters.com/fact-check/article1",
            "https://apnews.com/article/2",
            "https://www.bbc.com/news/3",
            "https://www.snopes.com/fact-check/4",
            "https://politifact.com/truth-o-meter/5",
            "https://factcheck.org/2026/01/6",
            "https://www.who.int/emergencies/7",
            "https://cdc.gov/alerts/8",
            "https://harvard.edu/news/9",
            "https://oxford.ac.uk/research/10",
        ]
        for url in high_urls:
            with self.subTest(url=url):
                self.assertEqual(get_credibility_tier(url), "high")

    def test_medium_credibility_domains(self):
        medium_urls = [
            "https://www.cnn.com/2026/world/1",
            "https://techcrunch.com/2026/enterprise/2",
            "https://www.wired.com/story/3",
            "https://www.forbes.com/sites/4",
            "https://thehindu.com/news/5",
            "https://www.nature.com/articles/6",
            "https://theverge.com/2026/7",
        ]
        for url in medium_urls:
            with self.subTest(url=url):
                self.assertEqual(get_credibility_tier(url), "medium")

    def test_low_credibility_domains(self):
        low_urls = [
            "https://random-viral-blog.blogspot.com/post/1",
            "https://unknown-leak-portal.xyz/story/2",
            "https://reddit.com/r/deepfakes/3",
            "https://x.com/user/status/4",
            "https://anon-news.medium.com/5",
        ]
        for url in low_urls:
            with self.subTest(url=url):
                self.assertEqual(get_credibility_tier(url), "low")


class TestStanceClassification(unittest.TestCase):
    """Test stance classification behaviors."""

    def test_heuristic_contradiction(self):
        claim = "The CEO admitted to fraud and resigned."
        clean_text = "Forensic analysis revealed this video is an AI deepfake. The executive remains in office and never made the statements."
        res = _deterministic_heuristic_fallback(claim, clean_text)
        self.assertEqual(res["stance"], "contradicts")

    def test_heuristic_support(self):
        claim = "The CEO admitted to fraud and resigned."
        clean_text = "Insiders confirmed the CEO announced his immediate resignation and admitted to massive losses in a leaked town hall."
        res = _deterministic_heuristic_fallback(claim, clean_text)
        self.assertEqual(res["stance"], "supports")

    def test_heuristic_context(self):
        claim = "The CEO admitted to fraud and resigned."
        clean_text = "Deepfake technology and executive impersonation scams have increased significantly across enterprise businesses this year."
        res = _deterministic_heuristic_fallback(claim, clean_text)
        self.assertEqual(res["stance"], "context")


class TestEndToEndMockContract(unittest.TestCase):
    """Test end-to-end processing of mock_input.json against the locked contract."""

    def test_mock_input_execution(self):
        mock_file = os.path.join(os.path.dirname(__file__), "mock_input.json")
        self.assertTrue(os.path.exists(mock_file), "mock_input.json must exist")

        with open(mock_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        agent = AnalysisAgent()
        output = agent.run(data)

        # 1. Output structure check
        self.assertIn("per_source", output)
        self.assertIsInstance(output["per_source"], list)
        self.assertEqual(len(output["per_source"]), 3)

        # 2. Schema check for each item in per_source
        allowed_stances = {"supports", "contradicts", "context"}
        allowed_tiers = {"high", "medium", "low"}

        for item in output["per_source"]:
            self.assertIn("url", item)
            self.assertIn("stance", item)
            self.assertIn("credibility_tier", item)

            self.assertIn(item["stance"], allowed_stances)
            self.assertIn(item["credibility_tier"], allowed_tiers)

        # 3. Specific expected classifications for our 3 mock sources
        sources = output["per_source"]
        
        # Source 1: Reuters Fact Check -> high tier, contradicts
        self.assertIn("reuters.com", sources[0]["url"])
        self.assertEqual(sources[0]["credibility_tier"], "high")
        self.assertEqual(sources[0]["stance"], "contradicts")

        # Source 2: Blogspot -> low tier, supports
        self.assertIn("blogspot.com", sources[1]["url"])
        self.assertEqual(sources[1]["credibility_tier"], "low")
        self.assertEqual(sources[1]["stance"], "supports")

        # Source 3: TechCrunch -> medium tier, context
        self.assertIn("techcrunch.com", sources[2]["url"])
        self.assertEqual(sources[2]["credibility_tier"], "medium")
        self.assertEqual(sources[2]["stance"], "context")


if __name__ == "__main__":
    unittest.main(verbosity=2)
