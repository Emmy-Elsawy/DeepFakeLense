# Multi-platform Dockerfile for DeepFakeLens FastAPI Backend
# Compatible with Hugging Face Spaces, Render, and Local Docker

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    CORS_ORIGINS="*"

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (HF Spaces defaults to 7860, Render uses dynamic $PORT)
EXPOSE 8000 7860

# Command to run uvicorn with shell variable expansion for $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
