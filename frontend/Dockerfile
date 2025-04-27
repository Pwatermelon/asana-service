FROM python:3.11-bullseye

WORKDIR /app

# Install system dependencies required by aiohttp
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc-dev \
    python3-dev \
    libffi-dev \
    && pip install --upgrade pip \
    && pip install wheel \
    && rm -rf /var/lib/apt/lists/*

COPY ./app /app/app
COPY requirements.txt .

# Install multidict first (aiohttp dependency), then other requirements
RUN pip install multidict==6.0.2 \
    && pip install -r requirements.txt

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:3000", "--workers", "2"]
