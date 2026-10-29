FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1
ENV KMP_DUPLICATE_LIB_OK=TRUE

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl wget git \
    libmupdf-dev mupdf-tools \
    tesseract-ocr \
    libtesseract-dev \
    libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p storage/uploads storage/indexes models

# Pre-cache embedding models so container starts fast with zero runtime download
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

EXPOSE 8000
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 0

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
