FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем файл онтологии и устанавливаем права доступа
RUN touch ontology_updated.owl && \
    chmod 666 ontology_updated.owl

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
