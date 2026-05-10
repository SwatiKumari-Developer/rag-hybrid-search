# Use slim Python image to reduce container size
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
# libpq-dev: PostgreSQL client library needed by psycopg2
# gcc: Compiler needed for some Python packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker cache optimization)
# If requirements don't change, Docker reuses this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model during build
# This avoids slow first-request downloads in production
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', quiet=True)"

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Start the FastAPI server with Uvicorn
# --host 0.0.0.0: Listen on all interfaces (required in containers)
# --workers 2: Multiple worker processes for concurrency
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
