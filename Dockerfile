# Use Python 3.13 slim as base image
FROM python:3.13-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r jenkins-failures && useradd -r -g jenkins-failures jenkins-failures

# Change ownership of the app directory
RUN chown -R jenkins-failures:jenkins-failures /app

# Switch to non-root user
USER jenkins-failures

# Default command
CMD ["python", "main.py"]
