import httpx
import os

# Используем localhost если BACKEND_URL не установлен
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

async def login(username: str, password: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
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
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Login error: {str(e)}")
            raise Exception("Invalid username or password")

async def get_asanas(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/asanas", headers=headers)
        response.raise_for_status()
        return response.json()

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
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Создаем multipart form data
    files = {
        "photo": ("image.png", photo, "image/png")
    }
    
    data = {
        "selected_name": selected_name if selected_name != "new" else None,
        "new_name_ru": new_name_ru,
        "new_name_en": new_name_en,
        "new_name_sanskrit": new_name_sanskrit,
        "selected_source": selected_source if selected_source != "new" else None,
        "new_source_title": new_source_title,
        "new_source_author": new_source_author,
        "new_source_year": new_source_year
    }
    
    # Удаляем None значения
    data = {k: v for k, v in data.items() if v is not None}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/asana",
            headers=headers,
            data=data,
            files=files
        )
        response.raise_for_status()
        return response.json()

async def get_sources(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/sources", headers=headers)
        response.raise_for_status()
        return response.json()

async def get_names(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/asana-names", headers=headers)
        response.raise_for_status()
        return response.json()