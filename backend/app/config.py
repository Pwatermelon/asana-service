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

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DB = os.getenv("POSTGRES_DB", "asana_auth")
POSTGRES_USER = os.getenv("POSTGRES_USER", "asana_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "asana_pass")
SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
