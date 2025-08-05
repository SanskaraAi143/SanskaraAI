# Use an official Python runtime as a parent image
FROM python:3.13-alpine

# Set the working directory in the container
WORKDIR /app

# Install Rust, Cargo, and necessary build dependencies, including GEOS and NumPy development headers
RUN apk add --no-cache \
      build-base \
      curl \
      git \
      libffi-dev \
      openssl-dev \
      pkgconfig \
      rust \
      cargo \
      nodejs \
      npm \
      geos-dev \
      py3-numpy-dev

# Copy the requirements file and install the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir uv
# Set the environment variable for pyo3 before installing dependencies
RUN PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 uv pip install --no-cache-dir -r requirements.txt --system

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8765

# Run the application
CMD ["python", "main.py"]