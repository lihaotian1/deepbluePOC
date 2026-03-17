FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY chapter_splitter.py /app/chapter_splitter.py
COPY data /app/data

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend:/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
