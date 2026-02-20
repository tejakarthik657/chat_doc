FROM python:3.11-slim

# System deps for PyMuPDF + compilation
RUN apt-get update && apt-get install -y \
    gcc g++ curl wget git \
    libmupdf-dev mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage dirs
RUN mkdir -p storage/uploads storage/indexes models

# Download embedding model at build time (so runtime is fast)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./models')"

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
