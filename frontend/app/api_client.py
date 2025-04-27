import httpx
import os
import logging
from typing import Optional, Dict
import asyncio
import aiohttp

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

async def add_asana(selected_name, selected_source, new_name_ru, new_name_en, 
                new_name_sanskrit, new_source_title, new_source_author, new_source_year, 
                photo=None, token=None):
    if not token:
        raise ValueError("Token is required for authentication")

    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Prepare form data
    form_data = aiohttp.FormData()
    form_data.add_field("selected_name", selected_name)
    form_data.add_field("selected_source", selected_source)
    
    if new_name_ru:
        form_data.add_field("new_name_ru", new_name_ru)
    if new_name_en:
        form_data.add_field("new_name_en", new_name_en)
    if new_name_sanskrit:
        form_data.add_field("new_name_sanskrit", new_name_sanskrit)
    if new_source_title:
        form_data.add_field("new_source_title", new_source_title)
    if new_source_author:
        form_data.add_field("new_source_author", new_source_author)
    if new_source_year:
        form_data.add_field("new_source_year", str(new_source_year))
    
    if photo:
        form_data.add_field("photo", photo, filename="photo.jpg", content_type="image/jpeg")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}/asana",
                headers=headers,
                data=form_data
            ) as response:
                if response.status == 401:
                    raise ValueError("Authentication token is invalid or expired")
                
                response_data = await response.json()
                if not response.ok:
                    error_msg = response_data.get("detail", "Unknown error occurred")
                    raise ValueError(f"API request failed: {error_msg}")
                
                return {"success": True, "data": response_data}
    except aiohttp.ClientError as e:
        raise ValueError(f"Failed to communicate with API: {str(e)}")

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

async def delete_source(source_id: str, token: str):
    logger.info(f"Deleting source with ID: {source_id}")
    try:
        response = await make_request(
            "DELETE",
            f"{BACKEND_URL}/sources/{source_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        logger.info("Successfully deleted source")
        return response
    except Exception as e:
        logger.error(f"Error deleting source: {str(e)}")
        raise

async def delete_name(name_id: str, token: str):
    logger.info(f"Deleting asana name with ID: {name_id}")
    try:
        response = await make_request(
            "DELETE",
            f"{BACKEND_URL}/asana-names/{name_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        logger.info("Successfully deleted asana name")
        return response
    except Exception as e:
        logger.error(f"Error deleting asana name: {str(e)}")
        raise