# API image for Render. Build context is this directory (api/).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# WeasyPrint (evidence PDFs) needs Pango and a font; tzdata is for the scheduler's time zone.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Render sets PORT. The free tier has no persistent disk, so seed whenever the database is empty.
EXPOSE 10000
CMD ["sh", "-c", "python seed.py --if-empty && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
