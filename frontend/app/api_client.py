import httpx
import os
import logging
from typing import Optional, Dict, List, Any
import asyncio
from urllib.parse import quote

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

async def login(username: str, password: str, remember_me: bool = False):
    logger.info(f"Attempting login for user: {username}")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/login",
            json={
                "username": username,
                "password": password,
                "remember_me": remember_me
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        logger.info("Login successful")
        return response
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise Exception("Invalid username or password")

async def register(username: str, email: str, first_name: str, last_name: str, password: str):
    logger.info(f"Registering new user: {username}, {email}")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/register",
            json={
                "username": username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "password": password
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        logger.info("Registration successful")
        return response
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise

async def confirm_registration(code: str):
    logger.info(f"Confirming registration with code")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/confirm-registration",
            json={"code": code},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        logger.info("Registration confirmation successful")
        return response
    except Exception as e:
        logger.error(f"Registration confirmation error: {str(e)}")
        raise

async def reset_password_request(email: str):
    logger.info(f"Requesting password reset for email")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/reset-password-request",
            json={"email": email},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        logger.info("Password reset request successful")
        return response
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        raise

async def reset_password_confirm(code: str, new_password: str):
    logger.info(f"Confirming password reset with code")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/reset-password-confirm",
            json={
                "code": code,
                "new_password": new_password
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        logger.info("Password reset confirmation successful")
        return response
    except Exception as e:
        logger.error(f"Password reset confirmation error: {str(e)}")
        raise

async def get_asanas(token: Optional[str] = None):
    logger.info("Fetching asanas list")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/asanas",
            headers=headers
        )
        logger.info(f"Successfully fetched asanas")
        return response
    except Exception as e:
        logger.error(f"Error fetching asanas: {str(e)}")
        raise

async def get_asanas_by_letter(letter: str, token: Optional[str] = None):
    logger.info(f"Fetching asanas starting with letter: {letter}")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/asanas/by-letter/{letter}",
            headers=headers
        )
        logger.info(f"Successfully fetched asanas for letter: {letter}")
        return response
    except Exception as e:
        logger.error(f"Error fetching asanas by letter: {str(e)}")
        raise

async def get_asanas_by_source(source_id: str, token: Optional[str] = None):
    logger.info(f"Fetching asanas for source: {source_id}")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/asanas/by-source/{source_id}",
            headers=headers
        )
        logger.info(f"Successfully fetched asanas for source: {source_id}")
        return response
    except Exception as e:
        logger.error(f"Error fetching asanas by source: {str(e)}")
        raise

async def search_asanas(query: str, fuzzy: bool = True, token: Optional[str] = None):
    logger.info(f"Searching asanas with query: {query}, fuzzy: {fuzzy}")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/asanas/search?query={quote(query)}&fuzzy={str(fuzzy).lower()}",
            headers=headers
        )
        logger.info(f"Successfully searched asanas with query: {query}")
        return response
    except Exception as e:
        logger.error(f"Error searching asanas: {str(e)}")
        raise

async def add_asana(selected_name, selected_source, new_name_ru, new_name_en, 
                new_name_sanskrit, transliteration=None, translation=None,
                new_source_title=None, new_source_author=None, new_source_year=None, 
                new_source_publisher=None, new_source_pages=None, new_source_annotation=None,
                photo=None, token=None):
    if not token:
        raise ValueError("Token is required for authentication")

    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Prepare form data using httpx's Files and data
    files = {}
    data = {
        "selected_name": selected_name,
        "selected_source": selected_source
    }
    
    if new_name_ru:
        data["new_name_ru"] = new_name_ru
    if new_name_en:
        data["new_name_en"] = new_name_en
    if new_name_sanskrit:
        data["new_name_sanskrit"] = new_name_sanskrit
    if transliteration:
        data["transliteration"] = transliteration
    if translation:
        data["translation"] = translation
        
    if new_source_title:
        data["new_source_title"] = new_source_title
    if new_source_author:
        data["new_source_author"] = new_source_author
    if new_source_year:
        data["new_source_year"] = str(new_source_year)
    if new_source_publisher:
        data["new_source_publisher"] = new_source_publisher
    if new_source_pages:
        data["new_source_pages"] = str(new_source_pages)
    if new_source_annotation:
        data["new_source_annotation"] = new_source_annotation
    
    if photo:
        files["photo"] = ("photo.jpg", photo, "image/jpeg")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/asana",
                headers=headers,
                data=data,
                files=files
            )
            if response.status_code == 401:
                raise ValueError("Authentication token is invalid or expired")
            
            response_data = response.json()
            if not response.is_success:
                error_msg = response_data.get("detail", "Unknown error occurred")
                raise ValueError(f"API request failed: {error_msg}")
            
            return {"success": True, "data": response_data}
    except httpx.RequestError as e:
        raise ValueError(f"Failed to communicate with API: {str(e)}")

async def get_sources(token: Optional[str] = None):
    logger.info("Fetching sources list")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/sources",
            headers=headers
        )
        logger.info(f"Successfully fetched sources")
        return response
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        raise

async def get_names(token: Optional[str] = None):
    logger.info("Fetching asana names list")
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/asana-names",
            headers=headers
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
            f"{BACKEND_URL}/delete-source?uri={quote(source_id)}",
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
            f"{BACKEND_URL}/delete-asana-name?uri={quote(name_id)}",
            headers={"Authorization": f"Bearer {token}"}
        )
        logger.info("Successfully deleted asana name")
        return response
    except Exception as e:
        logger.error(f"Error deleting asana name: {str(e)}")
        raise

async def delete_asana(asana_id: str, token: str):
    logger.info(f"Deleting asana with ID: {asana_id}")
    try:
        response = await make_request(
            "DELETE",
            f"{BACKEND_URL}/asanas?uri={quote(asana_id)}",
            headers={"Authorization": f"Bearer {token}"}
        )
        logger.info("Successfully deleted asana")
        return response
    except Exception as e:
        logger.error(f"Error deleting asana: {str(e)}")
        raise

async def add_asana_photo(asana_id: str, photo: bytes, source_id: str, token: str):
    logger.info(f"Добавление дополнительного фото для асаны: {asana_id}")
    headers = {"Authorization": f"Bearer {token}"}
    files = {"photo": ("photo.jpg", photo, "image/jpeg")}
    data = {"source_id": source_id}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/asana/{quote(asana_id)}/add-photo",
            headers=headers,
            data=data,
            files=files
        )
        response.raise_for_status()
        return response.json()

async def get_about_project():
    logger.info("Fetching about project info")
    try:
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/about-project"
        )
        logger.info(f"Successfully fetched about project info")
        return response
    except Exception as e:
        logger.error(f"Error fetching about project info: {str(e)}")
        raise

async def update_about_project(content: str, token: str):
    logger.info("Updating about project info")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/about-project",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": content}
        )
        logger.info(f"Successfully updated about project info")
        return response
    except Exception as e:
        logger.error(f"Error updating about project info: {str(e)}")
        raise

async def get_expert_instructions():
    logger.info("Fetching expert instructions")
    try:
        response = await make_request(
            "GET",
            f"{BACKEND_URL}/expert-instructions"
        )
        logger.info(f"Successfully fetched expert instructions")
        return response
    except Exception as e:
        logger.error(f"Error fetching expert instructions: {str(e)}")
        raise

async def update_expert_instructions(content: str, token: str):
    logger.info("Updating expert instructions")
    try:
        response = await make_request(
            "POST",
            f"{BACKEND_URL}/expert-instructions",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": content}
        )
        logger.info(f"Successfully updated expert instructions")
        return response
    except Exception as e:
        logger.error(f"Error updating expert instructions: {str(e)}")
        raise

async def upload_ontology(ontology_file: bytes, token: str):
    logger.info("Uploading ontology file")
    headers = {"Authorization": f"Bearer {token}"}
    files = {"ontology_file": ("ontology.owl", ontology_file, "application/rdf+xml")}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/upload-ontology",
            headers=headers,
            files=files
        )
        response.raise_for_status()
        return response.json()