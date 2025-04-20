import os

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Получаем абсолютный путь к файлу онтологии
OWL_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ontology_updated.owl")
