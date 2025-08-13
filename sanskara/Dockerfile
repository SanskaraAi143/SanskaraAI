FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libffi-dev \
    python3-dev \
    python3-numpy \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir uv
# Set the environment variable for pyo3 before installing dependencies
RUN PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 uv pip install --no-cache-dir -r requirements.txt --system

RUN uv pip install --upgrade pip
RUN uv pip install torch --extra-index-url https://download.pytorch.org/whl/cpu
RUN uv pip install -r requirements.txt

COPY . .
EXPOSE 8765
CMD ["python", "main.py"]
