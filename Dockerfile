FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y ffmpeg libmagic1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

COPY manage.py .
COPY requirements.txt .
COPY app/ ./app/
COPY phrases/ ./phrases/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh", "-c", "python manage.py migrate && daphne -b 0.0.0.0 -p 8000 app.asgi:application"]