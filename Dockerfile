FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
