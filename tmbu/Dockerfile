# Copyright (c) 2024 Qu Zhi
# All Rights Reserved.

# This software is proprietary and confidential.
# Unauthorized copying, distribution, or modification of this software is strictly prohibited.


# Use the Python slim image
FROM python:3.11-slim

# Install system dependencies for PostgreSQL and building C extensions
RUN apt-get update && apt-get install -y \ 
    libpq-dev \
    build-essential \
    gettext \
    netcat-openbsd \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*


# Install necessary libraries
RUN pip install nltk

# Set NLTK data path
ENV NLTK_DATA=/usr/src/tmbu/solutions/nltk_data

# Download NLTK resources
RUN python3 -m nltk.downloader -d /usr/src/tmbu/solutions/nltk_data punkt

# Set environment variables to avoid .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /usr/src/tmbu

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /opt/milvus

# Copy the rest of the Django project files into the container
COPY . .

COPY entrypoint.sh .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Set the cache directory for huggingface transformers and sentence-transformers
ENV HF_HOME=/usr/src/tmbu/solutions/huggingface

# Pre-download the model during the build process
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Expose the port for Django (default 8000)
EXPOSE 8000 


# Run Gunicorn as the default command; Milvus will be in a separate container (for production)
# CMD ["gunicorn", "tmbu.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=9", "--timeout=120", "--access-logfile", "-"]


