import asyncio
import json
import logging
from typing import Dict, List, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import trafilatura
import tiktoken

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Approx 500-800 tokens. 800 tokens max limit.
MAX_TOKENS = 1000

def truncate_to_tokens(text: str, max_tokens: int = MAX_TOKENS) -> str:
    if not text:
        return ""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        if len(tokens) > max_tokens:
            truncated = enc.decode(tokens[:max_tokens])
            return truncated + "..."
        return text
    except Exception as e:
        # Fallback to simple split if tiktoken is missing
        logging.warning(f"Tiktoken error, falling back to split: {e}")
        words = text.split()
        if len(words) > max_tokens * 0.75:
            return " ".join(words[:int(max_tokens * 0.75)]) + "..."
        return text

async def scrape_url(context, url: str, timeout_ms: int = 10000) -> Dict[str, Any]:
    page = await context.new_page()
    result = {"url": url, "title": "", "clean_text": ""}
    try:
        logging.info(f"Navigating to {url}")
        await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        
        # Give a small buffer for late JS rendering if needed
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except PlaywrightTimeoutError:
            pass # Ignore if network is not completely idle
        
        html_content = await page.content()
        title = await page.title()
        
        # Use trafilatura to extract clean text
        clean_text = trafilatura.extract(
            html_content, 
            include_comments=False, 
            include_tables=False, 
            no_fallback=False
        )
        
        if clean_text:
            truncated_text = truncate_to_tokens(clean_text, MAX_TOKENS)
            result["title"] = title
            result["clean_text"] = truncated_text
            logging.info(f"Successfully scraped {url} (Clean: {len(clean_text)} chars, Truncated: {len(truncated_text)} chars)")
        else:
            logging.warning(f"Trafilatura failed to extract text from {url}")
            
    except PlaywrightTimeoutError:
        logging.error(f"Timeout while scraping {url}")
    except Exception as e:
        logging.error(f"Failed to scrape {url}: {str(e)}")
    finally:
        await page.close()
        
    return result

async def process_urls(urls: List[str]) -> List[Dict[str, Any]]:
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Block resources like images/media to speed up
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        
        # Optional: route interception to abort images/css
        async def intercept_route(route):
            if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
            else:
                await route.continue_()
        
        await context.route("**/*", intercept_route)

        tasks = [scrape_url(context, url) for url in urls]
        scraped_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, data in enumerate(scraped_data):
            if isinstance(data, Exception):
                logging.error(f"Error processing URL {urls[idx]}: {data}")
            elif data and data.get("clean_text"):
                results.append(data)
                
        await browser.close()
    return results

def run_scraper(input_data: Dict[str, Any]) -> Dict[str, Any]:
    urls = input_data.get("candidate_urls", [])
    if not urls:
        return {"sources": []}
    
    # Check if event loop is already running
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        # if running in jupyter/ipython etc.
        import nest_asyncio
        nest_asyncio.apply()
        
    sources = asyncio.run(process_urls(urls))
    return {"sources": sources}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            data = json.load(f)
    else:
        # Default mock input for quick test
        data = {
            "candidate_urls": [
            "https://www.reuters.com/technology/nvidia-talks-acquire-hugging-face-13-billion-deal-business-insider-reports-2026-08-27/",
            "https://www.bbc.com/news/articles/cz97ljy91zxo",
            "https://apnews.com/video/nearly-1000-missing-in-nepal-and-tibet-after-catastrophic-floods-caused-by-glacial-collapse-9d10c17b21f745fcb6cc2085f0d74131",
            "https://10.255.255.1/"
            ]
        }
    
    result = run_scraper(data)
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(result, indent=2))
