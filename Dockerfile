FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y ffmpeg libsndfile1 espeak-ng && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "import kokoro; kokoro.KPipeline(lang_code='e')" || true

COPY main.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "300", "main:app"]
