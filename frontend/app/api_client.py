import httpx
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

async def login(username: str, password: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        response.raise_for_status()
        return response.json()

async def get_asanas(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_URL}/asanas", headers=headers)
        response.raise_for_status()
        return response.json()

async def add_asana(name_ru: str, name_en: str, name_sanskrit: str, photo_base64: str, source: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name_ru": name_ru,
        "name_en": name_en,
        "name_sanskrit": name_sanskrit,
        "photo_base64": photo_base64,
        "source": source
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BACKEND_URL}/asana", headers=headers, json=payload)
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