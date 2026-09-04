# NOTE: verify this tag is actually published on Docker Hub before building --
# Python 3.14 is recent enough that availability isn't a given the way it is
# for older versions. Matches the local dev venv (Python 3.14.2).
FROM python:3.14-slim

WORKDIR /app

# System deps for building any C-extension wheels not shipped as manylinux
# wheels (transitively pulled in by chromadb/onnxruntime/sentence-transformers).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch explicitly, BEFORE requirements.txt -- the reranker
# only does CPU inference, but a plain `pip install` of sentence-transformers
# pulls the default PyPI torch wheel, which bundles the full CUDA/GPU stack
# (nvidia-*, cuda_pathfinder, etc.) unnecessarily, ~5GB+ of dead weight.
# Installing the CPU wheel first satisfies sentence-transformers' torch
# dependency without pulling any of that in.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-warm the cross-encoder reranker and Chroma's default embedding model at
# BUILD time, baked into this image layer -- avoids a slow/flaky cold start
# hitting Hugging Face Hub over the network on every fresh container.
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
RUN python -c "import chromadb; chromadb.PersistentClient(path='/tmp/warm').get_or_create_collection('warm').add(ids=['1'], documents=['warm'])"

COPY . .

RUN chmod +x docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
