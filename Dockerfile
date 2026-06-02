FROM python:3.11-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL source files — index.html must be here
COPY app.py .
COPY processor.py .
COPY video_analyzer.py .
COPY ai_planner.py .
COPY index.html .

# Create folders
RUN mkdir -p uploads outputs

EXPOSE 7860

CMD ["python", "app.py"]