import httpx
import os
import logging
from typing import Optional
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("asana_service.frontend.api")

# Используем localhost если BACKEND_URL не установлен
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
logger.info(f"Using backend URL: {BACKEND_URL}")

# Максимальное количество попыток повторного подключения
MAX_RETRIES = 3
RETRY_DELAY = 1  # секунды

async def make_request(method: str, url: str, headers: Optional[dict] = None, **kwargs):
    """Общая функция для выполнения HTTP запросов с повторными попытками"""
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    timeout=30.0,  # Увеличиваем таймаут
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:  # Unauthorized
                logger.error("Authentication error")
                raise
            logger.warning(f"Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            if attempt == MAX_RETRIES - 1:
                raise
        await asyncio.sleep(RETRY_DELAY)

async def login(username: str, password: str):
    logger.info(f"Attempting login for user: {username}")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/token",
            data={
                "username": username,
                "password": password,
                "grant_type": "password"
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
        )
        logger.info("Login successful")
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise Exception("Invalid username or password")

async def get_asanas(token: str):
    logger.info("Fetching asanas list")
    try:
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/asanas",
            headers={"Authorization": f"Bearer {token}"}
        )
        logger.info(f"Successfully fetched asanas")
        return response
    except Exception as e:
        logger.error(f"Error fetching asanas: {str(e)}")
        raise

async def add_asana(
    selected_name: str = None,
    new_name_ru: str = None,
    new_name_en: str = None,
    new_name_sanskrit: str = None,
    selected_source: str = None,
    new_source_title: str = None,
    new_source_author: str = None,
    new_source_year: str = None,
    photo: bytes = None,
    token: str = None
):
    logger.info("Starting to add new asana")
    logger.debug(f"Parameters: selected_name={selected_name}, selected_source={selected_source}")
    
    files = {
        "photo": ("image.png", photo, "image/png")
    } if photo else None
    
    data = {
        "selected_name": selected_name,
        "new_name_ru": new_name_ru,
        "new_name_en": new_name_en,
        "new_name_sanskrit": new_name_sanskrit,
        "selected_source": selected_source,
        "new_source_title": new_source_title,
        "new_source_author": new_source_author,
        "new_source_year": new_source_year
    }
    
    # Удаляем None значения
    data = {k: v for k, v in data.items() if v is not None}
    
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/asana",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files
        )
        logger.info(f"Successfully added asana: {response}")
        return response
    except Exception as e:
        logger.error(f"Error adding asana: {str(e)}")
        raise

async def get_sources(token: str):
    logger.info("Fetching sources list")
    try:
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/sources",
            headers={"Authorization": f"Bearer {token}"}
        )
        logger.info(f"Successfully fetched sources")
        return response
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        raise

async def get_names(token: str):
    logger.info("Fetching asana names list")
    try:
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/asana-names",
            headers={"Authorization": f"Bearer {token}"}
        )
        logger.info(f"Successfully fetched asana names")
        return response
    except Exception as e:
        logger.error(f"Error fetching asana names: {str(e)}")
        raise