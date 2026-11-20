# Container for hosting the tutoring app (student pages, teacher dashboard, Science Buddy).
# Data (SQLite database and kept photos) lives in /data, which the host should keep on a persistent disk.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    TUTOR_DB=/data/tutor.db \
    TUTOR_PHOTOS=/data/photos

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data

# Hosts set PORT automatically; 8000 is the default for local runs.
CMD ["sh", "-c", "python -m uvicorn tutor.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
