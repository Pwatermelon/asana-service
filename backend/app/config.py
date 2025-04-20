import os
import logging
import sys

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # Увеличиваем до 24 часов

# Создаем путь к файлу онтологии внутри контейнера
OWL_FILE_PATH = "/app/ontology_updated.owl"

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("asana_service")
