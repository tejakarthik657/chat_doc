.PHONY: setup dev download-model docker-build docker-run test clean

# ── Setup ──────────────────────────────────────────────────────────────────────

setup:
	python -m venv venv
	./venv/bin/pip install -r requirements.txt
	cp .env.example .env
	mkdir -p storage/uploads storage/indexes models
	@echo "\n✅ Setup complete. Edit .env then run: make download-model && make dev"

# ── Local LLM ─────────────────────────────────────────────────────────────────

download-model:
	@echo "Downloading TinyLlama GGUF (~700MB)..."
	mkdir -p models
	wget -q --show-progress \
		https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
		-O models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
	@echo "✅ Model downloaded to models/"

# ── Dev server ────────────────────────────────────────────────────────────────
# Use "make dev" (no reload) when debugging auth/CORS - reload causes restarts mid-request
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# Use "make dev-reload" only when actively editing code (triggers restarts on file change)
dev-reload:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t rag-backend .

docker-run:
	docker run -d \
		--name rag-backend \
		-p 8000:8000 \
		--env-file .env \
		-v $(PWD)/storage:/app/storage \
		-v $(PWD)/models:/app/models \
		rag-backend

docker-stop:
	docker stop rag-backend && docker rm rag-backend

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

# ── Clean ─────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf storage/uploads/* storage/indexes/*
	@echo "✅ Cleaned storage (models kept)"
