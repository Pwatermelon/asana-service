from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
from app import api_client
import logging
from fastapi.security.utils import get_authorization_scheme_param

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("asana_service.frontend.web")

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Сессия по токену с использованием IP и User-Agent для дополнительной безопасности
session_tokens = {}

async def get_current_token(request: Request) -> Optional[str]:
    """Получает текущий токен с учетом IP и User-Agent"""
    client_id = f"{request.client.host}_{request.headers.get('user-agent', '')}"
    token = session_tokens.get(client_id)
    if token:
        logger.debug(f"Found token for client {client_id[:30]}...")
        return token
    logger.debug(f"No token found for client {client_id[:30]}...")
    return None

async def set_token(request: Request, token: str):
    """Сохраняет токен с учетом IP и User-Agent"""
    client_id = f"{request.client.host}_{request.headers.get('user-agent', '')}"
    session_tokens[client_id] = token
    logger.info(f"Saved token for client {client_id[:30]}...")

async def remove_token(request: Request):
    """Удаляет токен"""
    client_id = f"{request.client.host}_{request.headers.get('user-agent', '')}"
    if client_id in session_tokens:
        del session_tokens[client_id]
        logger.info(f"Removed token for client {client_id[:30]}...")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    token = await get_current_token(request)
    if token:
        return RedirectResponse("/asanas")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    
    logger.info(f"Login attempt from IP: {request.client.host}")
    logger.debug(f"Username provided: {username}")
    
    if not username or not password:
        logger.warning("Missing username or password in login attempt")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Username and password are required"}
        )
    
    try:
        token_data = await api_client.login(username, password)
        await set_token(request, token_data["access_token"])
        logger.info(f"Successful login for user: {username}")
        return RedirectResponse("/asanas", status_code=303)
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"}
        )

@app.get("/logout")
async def logout(request: Request):
    logger.info(f"Logout request from IP: {request.client.host}")
    await remove_token(request)
    return RedirectResponse("/login", status_code=303)

@app.get("/asanas", response_class=HTMLResponse)
async def asanas_list(request: Request):
    token = await get_current_token(request)
    if not token:
        logger.warning(f"Unauthorized access attempt to asanas from IP: {request.client.host}")
        return RedirectResponse("/login")
    
    try:
        logger.info("Fetching asanas list")
        asanas = await api_client.get_asanas(token)
        logger.info(f"Retrieved {len(asanas)} asanas")
        return templates.TemplateResponse("asana_list.html", {"request": request, "asanas": asanas})
    except Exception as e:
        logger.error(f"Error fetching asanas: {str(e)}")
        if "401" in str(e):
            await remove_token(request)
            return RedirectResponse("/login")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load asanas. Please try again later."
        })

@app.get("/asana/add", response_class=HTMLResponse)
async def add_asana_page(request: Request):
    token = await get_current_token(request)
    if not token:
        logger.warning(f"Unauthorized access attempt to add asana page from IP: {request.client.host}")
        return RedirectResponse("/login")

    try:
        logger.info("Loading add asana form data")
        sources = await api_client.get_sources(token)
        names = await api_client.get_names(token)
        logger.debug(f"Loaded {len(sources)} sources and {len(names)} names")

        return templates.TemplateResponse("add_asana.html", {
            "request": request,
            "sources": sources,
            "names": names,
            "token": token  # Добавляем токен в контекст шаблона
        })
    except Exception as e:
        logger.error(f"Error loading add asana form data: {str(e)}")
        if "401" in str(e):
            await remove_token(request)
            return RedirectResponse("/login")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load form data. Please try again later."
        })

@app.post("/asana/add", response_class=HTMLResponse)
async def add_asana(
    request: Request,
    token: str = Form(...),
    selected_name: str = Form(...),
    selected_source: str = Form(...),
    new_name_ru: Optional[str] = Form(None),
    new_name_en: Optional[str] = Form(None),
    new_name_sanskrit: Optional[str] = Form(None),
    new_source_title: Optional[str] = Form(None),
    new_source_author: Optional[str] = Form(None),
    new_source_year: Optional[str] = Form(None),
    photo: UploadFile = File(...)
):
    try:
        # Отладочный вывод
        logger.debug(f"Received form data - token: {token}, selected_name: {selected_name}, selected_source: {selected_source}")
        
        stored_token = await get_current_token(request)
        if not stored_token or stored_token != token:
            logger.warning(f"Token mismatch or unauthorized access attempt from IP: {request.client.host}")
            return RedirectResponse("/login")

        # Validate form data
        if selected_name == "new" and not all([new_name_ru, new_name_en, new_name_sanskrit]):
            logger.error("Missing required name fields for new name")
            raise ValueError("При добавлении нового названия все языковые поля обязательны")
            
        if selected_source == "new" and not all([new_source_title, new_source_author, new_source_year]):
            logger.error("Missing required source fields for new source")
            raise ValueError("При добавлении нового источника все поля источника обязательны")

        # Получаем содержимое файла
        photo_content = await photo.read()
        logger.debug(f"Read photo content, size: {len(photo_content)} bytes")
        
        # Отправляем данные через API клиент
        result = await api_client.add_asana(
            selected_name=selected_name,
            new_name_ru=new_name_ru,
            new_name_en=new_name_en,
            new_name_sanskrit=new_name_sanskrit,
            selected_source=selected_source,
            new_source_title=new_source_title,
            new_source_author=new_source_author,
            new_source_year=new_source_year if new_source_year else None,
            photo=photo_content,
            token=token
        )
        logger.info(f"Successfully added asana: {result}")
        return RedirectResponse("/asanas", status_code=303)
    except Exception as e:
        logger.error(f"Error adding asana: {str(e)}")
        if "401" in str(e):
            await remove_token(request)
            return RedirectResponse("/login")
        # В случае ошибки возвращаем на форму с сообщением об ошибке
        try:
            sources = await api_client.get_sources(token)
            names = await api_client.get_names(token)
            return templates.TemplateResponse("add_asana.html", {
                "request": request,
                "sources": sources,
                "names": names,
                "error": str(e),
                "token": token
            })
        except:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "An error occurred. Please try again later."
            })
