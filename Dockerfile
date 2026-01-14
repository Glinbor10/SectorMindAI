# Base image (Rasa 3.6 supports up to Python 3.10)
FROM python:3.10-slim

# Prevent Python from buffering and writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create and use a virtual environment inside the container
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Workdir
WORKDIR /app

# Install system dependencies only if needed (for python-Levenshtein compilation)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Upgrade setuptools before installing requirements (fixes randomname compatibility)
RUN pip install --upgrade setuptools wheel

# Install Python dependencies first (leverages Docker layer cache)
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copy application source
COPY backend /app/backend
COPY frontend /app/frontend
COPY database /app/database
COPY docs /app/docs

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose Flask port
EXPOSE 5000

# Use entrypoint that runs migrations before Flask
ENTRYPOINT ["/app/docker-entrypoint.sh"]
