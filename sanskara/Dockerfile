FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libffi-dev \
    python3-dev \
    python3-numpy \
    libssl-dev \
    pkg-config \
    rustc \
    cargo \
    nodejs \
    npm \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir uv
RUN uv pip install --upgrade pip --system
RUN uv pip install torch --extra-index-url https://download.pytorch.org/whl/cpu --system
RUN uv pip install -r requirements.txt --system

COPY . .
EXPOSE 8765
CMD ["python", "main.py"]
