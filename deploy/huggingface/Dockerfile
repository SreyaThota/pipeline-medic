# Pipeline Medic demo for a Hugging Face Docker Space (CPU basic, free tier).
#
# Build context is the repository root:
#   docker build -f deploy/huggingface/Dockerfile -t pipeline-medic-demo .
#   docker run --rm -p 7860:7860 pipeline-medic-demo
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# CPU-only torch first, so sentence-transformers does not pull the CUDA build.
RUN pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
COPY demo/requirements.txt demo/requirements.txt
RUN pip install -r demo/requirements.txt

# Bake the embedding model into the image: no download at startup.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY app app
COPY agents agents
COPY mcp_server mcp_server
COPY rag rag
COPY demo demo
COPY data/sample_logs data/sample_logs

# Hugging Face runs Spaces as user 1000.
RUN useradd -m -u 1000 user && chown -R user /app
USER user

ENV HF_HUB_OFFLINE=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
EXPOSE 7860

CMD ["streamlit", "run", "demo/app.py"]
