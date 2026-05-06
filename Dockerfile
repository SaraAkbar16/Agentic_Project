FROM python:3.10-slim

# Install system dependencies
# ffmpeg: for video processing
# espeak, libasound2: for pyttsx3 (TTS)
# libsm6, libxext6: for OpenCV
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak \
    libasound2-dev \
    libsm6 \
    libxext6 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
# We use the main requirements.txt and backend requirements
COPY requirements.txt .
COPY backend/requirements.txt ./backend_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r backend_requirements.txt

# Copy project structure
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose backend port
EXPOSE 8001

# Run the backend
CMD ["python", "backend/main.py"]
