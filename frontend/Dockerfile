FROM python:3.11

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY ./app /app/app
COPY requirements.txt .

# Install aiohttp first with --no-build-isolation
RUN pip install --no-build-isolation aiohttp==3.8.1 && \
    pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:3000", "--workers", "2"]
