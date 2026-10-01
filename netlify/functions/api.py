import os
import sys
from fastapi.testclient import TestClient

# Point Netlify to your core parent directory scripts where main.py lives
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import your FastAPI app instance from your main.py file
from main import app

# Use FastAPI's lightweight testing client to simulate server routing internally
client = TestClient(app)

def handler(event, context):
    path = event.get("path", "").replace("/.netlify/functions/api", "")
    method = event.get("httpMethod", "GET")
    body = event.get("body", "")
    headers = event.get("headers", {})

    # Match and route the incoming POST request to your FastAPI /analyze route
    if path == "/analyze" or path == "analyze":
        response = client.post("/analyze", content=body, headers=headers)
        return {
            "statusCode": response.status_code,
            "headers": dict(response.headers),
            "body": response.text
        }
        
    # Catch-all fallbacks for base info paths
    response = client.get("/", headers=headers)
    return {
        "statusCode": response.status_code,
        "headers": dict(response.headers),
        "body": response.text
    }
