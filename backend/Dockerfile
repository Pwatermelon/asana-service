FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем файл онтологии и устанавливаем права доступа
RUN touch ontology_updated.owl && \
    chmod 666 ontology_updated.owl

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000", "--workers", "4", "--log-level", "debug"]
