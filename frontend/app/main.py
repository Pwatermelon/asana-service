from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Cookie, Response, Body, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
from app import api_client
import logging
import time
from jose import jwt
import os
import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("asana_service.frontend.web")

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Secret key for cookie encryption
SECRET_KEY = os.getenv("COOKIE_SECRET", "your-secret-key-12345")

# Token management functions
async def get_current_token(request: Request) -> Optional[str]:
    """Get token from encrypted cookie"""
    token_cookie = request.cookies.get("session_token")
    if not token_cookie:
        return None
    
    try:
        token_data = jwt.decode(token_cookie, SECRET_KEY, algorithms=["HS256"])
        token = token_data.get("token")
        expires_at = token_data.get("expires_at", 0)
        
        if token and time.time() < expires_at:
            logger.debug("Found valid token in cookie")
            return token
            
    except Exception as e:
        logger.error(f"Error decoding token cookie: {str(e)}")
    
    return None

async def get_user_role(request: Request) -> Optional[str]:
    """Get user role from encrypted cookie"""
    token_cookie = request.cookies.get("session_token")
    if not token_cookie:
        return None
    
    try:
        token_data = jwt.decode(token_cookie, SECRET_KEY, algorithms=["HS256"])
        return token_data.get("role")
            
    except Exception as e:
        logger.error(f"Error getting user role: {str(e)}")
    
    return None

async def set_token(response: Response, token: str, role: str):
    """Store token in encrypted cookie"""
    expires_at = time.time() + (7 * 24 * 60 * 60)  # 7 days
    token_data = {
        "token": token,
        "expires_at": expires_at,
        "role": role
    }
    encrypted_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
    response.set_cookie(
        key="session_token",
        value=encrypted_token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    logger.info("Saved token in cookie")

async def remove_token(response: Response):
    """Remove token cookie"""
    response.delete_cookie(key="session_token")
    logger.info("Removed token cookie")

async def get_token_for_api(request: Request) -> Optional[str]:
    """Get token from cookie for API requests"""
    token_cookie = request.cookies.get("session_token")
    if not token_cookie:
        return None
    
    try:
        token_data = jwt.decode(token_cookie, SECRET_KEY, algorithms=["HS256"])
        token = token_data.get("token")
        expires_at = token_data.get("expires_at", 0)
        
        if token and time.time() < expires_at:
            return token
            
    except Exception as e:
        logger.error(f"Error getting token for API: {str(e)}")
    
    return None

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    token = await get_current_token(request)
    if token:
        return RedirectResponse("/asanas")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user_role = await get_user_role(request)
    token = await get_current_token(request)
    is_admin = user_role == "admin"
    is_expert_or_admin = user_role in ["admin", "expert"]
    is_authenticated = token is not None
    return templates.TemplateResponse("login.html", {"request": request, "user_role": user_role, "is_admin": is_admin, "is_expert_or_admin": is_expert_or_admin, "is_authenticated": is_authenticated})

@app.post("/login", response_class=JSONResponse)
async def login(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        remember_me = data.get("remember_me", False)
        
        logger.info(f"Login attempt from IP: {request.client.host}")
        logger.debug(f"Username provided: {username}")
        
        if not username or not password:
            logger.warning("Missing username or password in login attempt")
            return JSONResponse(
                status_code=400,
                content={"detail": "Username and password are required"}
            )
        
        token_data = await api_client.login(username, password, remember_me)
        logger.info(f"Successful login for user: {username}")
        
        response = JSONResponse(content=token_data)
        await set_token(response, token_data["access_token"], token_data["role"])
        
        return response
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid username or password"}
        )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user_role = await get_user_role(request)
    token = await get_current_token(request)
    is_admin = user_role == "admin"
    is_expert_or_admin = user_role in ["admin", "expert"]
    is_authenticated = token is not None
    return templates.TemplateResponse("register.html", {"request": request, "user_role": user_role, "is_admin": is_admin, "is_expert_or_admin": is_expert_or_admin, "is_authenticated": is_authenticated})

@app.post("/register", response_class=JSONResponse)
async def register(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        email = data.get("email")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        password = data.get("password")
        
        logger.info(f"Registration attempt from IP: {request.client.host}")
        
        if not all([username, email, first_name, last_name, password]):
            logger.warning("Missing required fields in registration attempt")
            return JSONResponse(
                status_code=400,
                content={"detail": "All fields are required"}
            )
        
        result = await api_client.register(username, email, first_name, last_name, password)
        logger.info(f"Successful registration for user: {username}")
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/confirm-registration", response_class=HTMLResponse)
async def confirm_registration_page(request: Request):
    return templates.TemplateResponse("confirm_registration.html", {"request": request})

@app.post("/confirm-registration", response_class=JSONResponse)
async def confirm_registration(request: Request):
    try:
        data = await request.json()
        code = data.get("code")
        
        if not code:
            return JSONResponse(
                status_code=400,
                content={"detail": "Confirmation code is required"}
            )
        
        result = await api_client.confirm_registration(code)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Confirmation failed: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request})

@app.post("/reset-password-request", response_class=JSONResponse)
async def reset_password_request(request: Request):
    try:
        data = await request.json()
        email = data.get("email")
        
        if not email:
            return JSONResponse(
                status_code=400,
                content={"detail": "Email is required"}
            )
        
        result = await api_client.reset_password_request(email)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/reset-password-confirm", response_class=HTMLResponse)
async def reset_password_confirm_page(request: Request):
    return templates.TemplateResponse("reset_password_confirm.html", {"request": request})

@app.post("/reset-password-confirm", response_class=JSONResponse)
async def reset_password_confirm(request: Request):
    try:
        data = await request.json()
        code = data.get("code")
        new_password = data.get("new_password")
        
        if not code or not new_password:
            return JSONResponse(
                status_code=400,
                content={"detail": "Code and new password are required"}
            )
        
        result = await api_client.reset_password_confirm(code, new_password)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Password reset confirmation failed: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/logout")
async def logout(request: Request):
    logger.info(f"Logout request from IP: {request.client.host}")
    response = RedirectResponse("/login", status_code=303)
    await remove_token(response)
    return response

@app.get("/asanas", response_class=HTMLResponse)
async def asanas_list(request: Request):
    try:
        token = await get_token_for_api(request)
        user_role = await get_user_role(request)
        is_admin = user_role == "admin"
        is_expert_or_admin = user_role in ["admin", "expert"]
        is_authenticated = token is not None
        asanas = await api_client.get_asanas(token)
        grouped_asanas = {}
        for asana in asanas:
            first_letter = asana['name']['name_ru'][0].upper() if asana['name']['name_ru'] else "?"
            if first_letter not in grouped_asanas:
                grouped_asanas[first_letter] = []
            grouped_asanas[first_letter].append(asana)
        sorted_groups = sorted(grouped_asanas.items())
        alphabet = sorted(grouped_asanas.keys())
        return templates.TemplateResponse("asana_list.html", {
            "request": request, 
            "grouped_asanas": sorted_groups,
            "alphabet": alphabet,
            "is_admin": is_admin,
            "is_expert_or_admin": is_expert_or_admin,
            "is_authenticated": is_authenticated,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        })
    except Exception as e:
        logger.error(f"Error loading asanas: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load asanas"
        })

@app.get("/asanas/by-letter/{letter}", response_class=HTMLResponse)
async def asanas_by_letter(request: Request, letter: str):
    try:
        token = await get_token_for_api(request)
        user_role = await get_user_role(request)
        is_admin = user_role == "admin"
        is_expert_or_admin = user_role in ["admin", "expert"]
        is_authenticated = token is not None
        asanas = await api_client.get_asanas_by_letter(letter, token)
        all_asanas = await api_client.get_asanas(token)
        alphabet = sorted(set(asana['name']['name_ru'][0].upper() for asana in all_asanas if asana['name']['name_ru']))
        return templates.TemplateResponse("asana_list.html", {
            "request": request, 
            "asanas": asanas,
            "alphabet": alphabet,
            "current_letter": letter,
            "is_admin": is_admin,
            "is_expert_or_admin": is_expert_or_admin,
            "is_authenticated": is_authenticated,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        })
    except Exception as e:
        logger.error(f"Error loading asanas by letter: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load asanas"
        })

@app.get("/sources", response_class=HTMLResponse)
async def sources_list(request: Request):
    try:
        token = await get_token_for_api(request)
        user_role = await get_user_role(request)
        is_admin = user_role == "admin"
        is_expert_or_admin = user_role in ["admin", "expert"]
        is_authenticated = token is not None
        sources = await api_client.get_sources(token)
        sources.sort(key=lambda s: s.get('author', '').lower())
        return templates.TemplateResponse("sources.html", {
            "request": request,
            "sources": sources,
            "is_admin": is_admin,
            "is_expert_or_admin": is_expert_or_admin,
            "is_authenticated": is_authenticated,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        })
    except Exception as e:
        logger.error(f"Error loading sources: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load sources"
        })

@app.delete("/sources/{source_id}")
async def delete_source(source_id: str, request: Request):
    logger.info(f"FRONTEND: Получен запрос на удаление источника: {source_id}")
    token = await get_current_token(request)
    if not token:
        logger.error("FRONTEND: Нет токена авторизации!")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # Формируем полный URI источника
        full_uri = f"http://www.semanticweb.org/platinum_watermelon/ontologies/Asana#source_{source_id}"
        result = await api_client.delete_source(full_uri, token)
        logger.info(f"FRONTEND: Ответ от бэкенда: {result}")
        return {"message": "Source deleted successfully"}
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при удалении источника: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    try:
        about_data = await api_client.get_about_project()
        content = about_data.get('content', 'Информация о проекте отсутствует')
        user_role = await get_user_role(request)
        is_admin = user_role == "admin"
        is_expert_or_admin = user_role in ["admin", "expert"]
        is_authenticated = await get_current_token(request) is not None
        return templates.TemplateResponse("about_project.html", {
            "request": request,
            "content": content,
            "is_admin": is_admin,
            "is_expert_or_admin": is_expert_or_admin,
            "is_authenticated": is_authenticated,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        })
    except Exception as e:
        logger.error(f"Error loading about project: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load about project information"
        })

@app.post("/about-project", response_class=JSONResponse)
async def update_about_project(request: Request):
    token = await get_current_token(request)
    user_role = await get_user_role(request)
    
    if not token or user_role != "admin":
        return JSONResponse(
            status_code=403,
            content={"detail": "Only admins can update about project information"}
        )
    
    try:
        data = await request.json()
        content = data.get("content")
        
        if not content:
            return JSONResponse(
                status_code=400,
                content={"detail": "Content is required"}
            )
        
        result = await api_client.update_about_project(content, token)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error updating about project: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/expert-instructions", response_class=HTMLResponse)
async def expert_instructions_page(request: Request):
    try:
        instructions_data = await api_client.get_expert_instructions()
        content = instructions_data.get('content', 'Инструкции для экспертов отсутствуют')
        user_role = await get_user_role(request)
        is_admin = user_role == "admin"
        is_expert_or_admin = user_role in ["admin", "expert"]
        is_authenticated = await get_current_token(request) is not None
        return templates.TemplateResponse("expert_instructions.html", {
            "request": request,
            "content": content,
            "is_admin": is_admin,
            "is_expert_or_admin": is_expert_or_admin,
            "is_authenticated": is_authenticated,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        })
    except Exception as e:
        logger.error(f"Error loading expert instructions: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load expert instructions"
        })

@app.post("/expert-instructions", response_class=JSONResponse)
async def update_expert_instructions(request: Request):
    token = await get_current_token(request)
    user_role = await get_user_role(request)
    
    if not token or user_role != "admin":
        return JSONResponse(
            status_code=403,
            content={"detail": "Only admins can update expert instructions"}
        )
    
    try:
        data = await request.json()
        content = data.get("content")
        
        if not content:
            return JSONResponse(
                status_code=400,
                content={"detail": "Content is required"}
            )
        
        result = await api_client.update_expert_instructions(content, token)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error updating expert instructions: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user_role = await get_user_role(request)
    token = await get_current_token(request)
    is_admin = user_role == "admin"
    is_expert_or_admin = user_role in ["admin", "expert"]
    is_authenticated = token is not None
    context = {
        "request": request,
        "is_admin": is_admin,
        "is_expert_or_admin": is_expert_or_admin,
        "is_authenticated": is_authenticated,
        "user_role": user_role,
        "year": datetime.datetime.now().year
    }
    return templates.TemplateResponse("settings.html", context)

@app.post("/upload-ontology", response_class=JSONResponse)
async def upload_ontology(request: Request, ontology_file: UploadFile = File(...)):
    token = await get_current_token(request)
    user_role = await get_user_role(request)
    
    if not token or user_role != "admin":
        return JSONResponse(
            status_code=403,
            content={"detail": "Only admins can upload ontology file"}
        )
    
    try:
        file_content = await ontology_file.read()
        result = await api_client.upload_ontology(file_content, token)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error uploading ontology: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/asana/add", response_class=HTMLResponse)
async def add_asana_form(request: Request):
    token = await get_current_token(request)
    user_role = await get_user_role(request)
    is_admin = user_role == "admin"
    is_expert_or_admin = user_role in ["admin", "expert"]
    is_authenticated = token is not None
    if not token or user_role not in ["admin", "expert"]:
        return RedirectResponse("/login")
    try:
        names = await api_client.get_names()
        sources = await api_client.get_sources()
        return templates.TemplateResponse(
            "add_asana.html",
            {
                "request": request,
                "names": names,
                "sources": sources,
                "is_admin": is_admin,
                "is_expert_or_admin": is_expert_or_admin,
                "is_authenticated": is_authenticated,
                "user_role": user_role,
                "year": datetime.datetime.now().year
            }
        )
    except Exception as e:
        logger.error(f"Error loading data for add asana form: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Не удалось загрузить данные для формы добавления асаны"
        })

@app.get("/asana/{asana_id}-page", response_class=HTMLResponse)
async def asana_detail(request: Request, asana_id: str):
    try:
        logger.info(f"FRONTEND: Получен запрос на просмотр асаны: {asana_id}")
        token = await get_token_for_api(request)
        user_role = await get_user_role(request)
        is_admin = user_role == "admin"
        is_expert_or_admin = user_role in ["admin", "expert"]
        is_authenticated = token is not None
            
        logger.info("FRONTEND: Получаем список всех асан...")
        asanas = await api_client.get_asanas(token)
        
        # Добавляем префикс asana_ если его нет
        if not asana_id.startswith('asana_'):
            asana_id = f"asana_{asana_id}"
        
        # Формируем полный URI для сравнения
        full_uri = f"http://www.semanticweb.org/platinum_watermelon/ontologies/Asana#{asana_id}"
        asana = next((a for a in asanas if a.get('id') == full_uri), None)
        
        if not asana:
            logger.error(f"FRONTEND: Асана не найдена: {asana_id}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Асана не найдена"
            })
            
        sources = []
        if is_expert_or_admin and token:
            logger.info("FRONTEND: Получаем список источников для эксперта/админа...")
            sources = await api_client.get_sources(token)
            
        # Преобразуем источники фотографий в объекты
        if 'photos' in asana:
            for photo in asana['photos']:
                if isinstance(photo, dict) and isinstance(photo.get('source'), str):
                    source_id = photo['source'].split('#')[-1]
                    source = next((s for s in sources if s['id'] == photo['source']), None)
                    if source:
                        photo['source'] = source
            
        logger.info("FRONTEND: Отображаем страницу асаны")
        return templates.TemplateResponse("asana_detail.html", {
            "request": request,
            "asana": asana,
            "sources": sources,
            "is_expert_or_admin": is_expert_or_admin,
            "is_admin": is_admin,
            "is_authenticated": is_authenticated,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        })
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при загрузке деталей асаны: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Не удалось загрузить информацию об асане: {str(e)}"
        })

@app.post("/asana/{asana_id}/add-photo", response_class=JSONResponse)
async def add_asana_photo(request: Request, asana_id: str):
    token = await get_current_token(request)
    user_role = await get_user_role(request)
    
    if not token or user_role not in ["admin", "expert"]:
        return JSONResponse(
            status_code=403,
            content={"detail": "Only admins and experts can add photos"}
        )
    
    try:
        form = await request.form()
        photo = form.get("photo")
        source_id = form.get("source_id")
        
        if not photo or not source_id:
            return JSONResponse(
                status_code=400,
                content={"detail": "Photo and source are required"}
            )
        
        photo_bytes = await photo.read()
        result = await api_client.add_asana_photo(asana_id, photo_bytes, source_id, token)
        return JSONResponse(content={"success": True})
    except Exception as e:
        logger.error(f"Error adding asana photo: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)}
        )

@app.get("/sources/add", response_class=HTMLResponse)
async def add_source_form(request: Request):
    token = await get_token_for_api(request)
    user_role = await get_user_role(request)
    is_admin = user_role == "admin"
    is_expert_or_admin = user_role in ["admin", "expert"]
    is_authenticated = token is not None
    if not token or user_role not in ["admin", "expert"]:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "add_source.html",
        {
            "request": request,
            "is_expert_or_admin": is_expert_or_admin,
            "is_authenticated": is_authenticated,
            "is_admin": is_admin,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        }
    )

@app.get("/asana/{asana_id}/check-photo/{source_id}")
async def check_asana_photo(request: Request, asana_id: str, source_id: str):
    token = await get_token_for_api(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Проверяем наличие фото в источнике
        photo = await api_client.get_asana_photo_by_source(asana_id, source_id, token)
        return {"hasPhoto": photo is not None}
    except Exception as e:
        logger.error(f"Error checking asana photo: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/sources/{source_id}/asanas", response_class=HTMLResponse)
async def source_asanas(request: Request, source_id: str):
    try:
        logger.info(f"FRONTEND: Получен запрос на просмотр асан источника: {source_id}")
        token = await get_token_for_api(request)
        if not token:
            logger.error("FRONTEND: Нет токена авторизации!")
            return RedirectResponse("/login")
            
        user_role = await get_user_role(request)
        is_admin = user_role == "admin"
        is_expert_or_admin = user_role in ["admin", "expert"]
        is_authenticated = token is not None
        
        logger.info("FRONTEND: Получаем информацию об источнике...")
        # Извлекаем короткий ID, если передан полный URI
        short_source_id = source_id.split('#')[-1] if '#' in source_id else source_id
        if short_source_id.startswith('source_'):
            short_source_id = short_source_id[7:]  # Убираем префикс 'source_'
            
        source = await api_client.get_source(short_source_id, token)
        if not source:
            logger.error(f"FRONTEND: Источник не найден: {source_id}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Источник не найден"
            })
            
        logger.info("FRONTEND: Получаем список асан источника...")
        asanas = await api_client.get_asanas_by_source(short_source_id, token)
        
        # Добавляем логирование для проверки данных
        logger.info(f"FRONTEND: Получено {len(asanas)} асан")
        for asana in asanas:
            logger.info(f"FRONTEND: Асана {asana['name']['name_ru']} имеет фото: {'photo' in asana and bool(asana['photo'])}")
        
        grouped_asanas = {}
        for asana in asanas:
            first_letter = asana['name']['name_ru'][0].upper() if asana['name']['name_ru'] else "?"
            if first_letter not in grouped_asanas:
                grouped_asanas[first_letter] = []
            grouped_asanas[first_letter].append(asana)
        sorted_groups = dict(sorted(grouped_asanas.items()))
        alphabet = sorted(grouped_asanas.keys())
        
        logger.info(f"FRONTEND: Найдено {len(asanas)} асан для источника")
        return templates.TemplateResponse("source_asanas.html", {
            "request": request,
            "source": source,
            "grouped_asanas": sorted_groups,
            "alphabet": alphabet,
            "is_expert_or_admin": is_expert_or_admin,
            "is_admin": is_admin,
            "is_authenticated": is_authenticated,
            "user_role": user_role,
            "year": datetime.datetime.now().year
        })
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при загрузке асан источника: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Не удалось загрузить асаны источника: {str(e)}"
        })

@app.get("/api/asanas/search")
async def api_search_asanas(request: Request, query: str, fuzzy: bool = True):
    """API endpoint для поиска асан"""
    try:
        token = await get_token_for_api(request)
        results = await api_client.search_asanas(query, fuzzy, token)
        return results
    except Exception as e:
        logger.error(f"Error searching asanas: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/auth/check")
async def check_auth(request: Request):
    """API endpoint для проверки авторизации"""
    try:
        token = await get_current_token(request)
        user_role = await get_user_role(request)
        return {
            "is_authenticated": token is not None,
            "role": user_role
        }
    except Exception as e:
        logger.error(f"Error checking auth: {str(e)}")
        return {
            "is_authenticated": False,
            "role": None
        }

@app.get("/api/sources/search")
async def api_search_sources(request: Request, query: str):
    """API endpoint для поиска источников"""
    try:
        token = await get_token_for_api(request)
        sources = await api_client.get_sources(token)
        
        # Поиск по названию, автору и аннотации
        query = query.lower()
        results = []
        for source in sources:
            if (query in source.get("title", "").lower() or 
                query in source.get("author", "").lower() or 
                query in source.get("annotation", "").lower()):
                results.append(source)
        
        return results
    except Exception as e:
        logger.error(f"Error searching sources: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/asana", response_class=JSONResponse)
async def add_asana(request: Request):
    try:
        token = await get_token_for_api(request)
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Session expired. Please login again."})

        form = await request.form()
        result = await api_client.add_asana(
            selected_name=form.get("selected_name"),
            selected_source=form.get("selected_source"),
            new_name_ru=form.get("new_name_ru"),
            new_name_sanskrit=form.get("new_name_sanskrit"),
            transliteration=form.get("transliteration"),
            definition=form.get("definition"),
            new_source_title=form.get("new_source_title"),
            new_source_author=form.get("new_source_author"),
            new_source_year=int(form.get("new_source_year")) if form.get("new_source_year") else None,
            new_source_publisher=form.get("new_source_publisher"),
            new_source_pages=int(form.get("new_source_pages")) if form.get("new_source_pages") else None,
            new_source_annotation=form.get("new_source_annotation"),
            photo=await form.get("photo").read() if form.get("photo") else None,
            token=token
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error adding asana: {str(e)}")
        return JSONResponse(status_code=400, content={"detail": str(e)})

@app.post("/sources", response_class=JSONResponse)
async def add_source(request: Request):
    try:
        token = await get_token_for_api(request)
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Session expired. Please login again."})

        source_data = await request.json()
        result = await api_client.add_source(source_data, token)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error adding source: {str(e)}")
        return JSONResponse(status_code=400, content={"detail": str(e)})

@app.delete("/asanas/{asana_id}")
async def delete_asana(asana_id: str, request: Request):
    logger.info(f"FRONTEND: Получен запрос на удаление асаны: {asana_id}")
    token = await get_current_token(request)
    if not token:
        logger.error("FRONTEND: Нет токена авторизации!")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # Формируем полный URI асаны
        full_uri = f"http://www.semanticweb.org/platinum_watermelon/ontologies/Asana#asana_{asana_id}"
        result = await api_client.delete_asana(full_uri, token)
        logger.info(f"FRONTEND: Ответ от бэкенда: {result}")
        return {"message": "Asana deleted successfully"}
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при удалении асаны: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
