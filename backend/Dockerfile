FROM python:3.11-slim

WORKDIR /app

# System deps: ffmpeg for audio, libsndfile for librosa, build tools for llama-cpp-python
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 build-essential cmake && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 1) Install CPU-only PyTorch first (skips ~2.5GB of NVIDIA CUDA libs)
RUN pip install --no-cache-dir torch==2.5.1+cpu torchaudio==2.5.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# 2) Build llama-cpp-python with CPU-only (no CUDA compilation)
ENV CMAKE_ARGS="-DGGML_CUDA=OFF"
RUN pip install --no-cache-dir llama-cpp-python>=0.3.2

# 3) Install remaining deps (torch already satisfied, won't re-download)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent dirs — mount as volumes
RUN mkdir -p data uploads

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
