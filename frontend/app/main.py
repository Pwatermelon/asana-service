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

async def set_token(response: Response, token: str):
    """Store token in encrypted cookie"""
    expires_at = time.time() + (24 * 60 * 60)  # 24 hours
    token_data = {
        "token": token,
        "expires_at": expires_at
    }
    encrypted_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
    response.set_cookie(
        key="session_token",
        value=encrypted_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=24 * 60 * 60
    )
    logger.info("Saved token in secure cookie")

async def remove_token(response: Response):
    """Remove token cookie"""
    response.delete_cookie(key="session_token")
    logger.info("Removed token cookie")

# Routes
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
        response = RedirectResponse("/asanas", status_code=303)
        await set_token(response, token_data["access_token"])
        logger.info(f"Successful login for user: {username}")
        return response
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"}
        )

@app.get("/logout")
async def logout(request: Request):
    logger.info(f"Logout request from IP: {request.client.host}")
    response = RedirectResponse("/login", status_code=303)
    await remove_token(response)
    return response

@app.get("/asanas", response_class=HTMLResponse)
async def asanas_list(request: Request, search: Optional[str] = None):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    try:
        asanas = await api_client.get_asanas(token)
        if search:
            search_lower = search.lower()
            asanas = [a for a in asanas if search_lower in (a['name']['ru'] or '').lower() or search_lower in (a['name']['en'] or '').lower() or search_lower in (a['name']['sanskrit'] or '').lower()]
        return templates.TemplateResponse("asana_list.html", {"request": request, "asanas": asanas})
    except Exception as e:
        if "401" in str(e):
            response = RedirectResponse("/login", status_code=303)
            await remove_token(response)
            return response
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load asanas"
        })

@app.get("/sources", response_class=HTMLResponse)
async def sources_list(request: Request, search: Optional[str] = None):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    try:
        sources = await api_client.get_sources(token)
        if search:
            search_lower = search.lower()
            sources = [s for s in sources if search_lower in (s['title'] or '').lower() or search_lower in (s['author'] or '').lower() or search_lower in str(s['year'])]
        return templates.TemplateResponse("sources.html", {"request": request, "sources": sources})
    except Exception as e:
        if "401" in str(e):
            response = RedirectResponse("/login", status_code=303)
            await remove_token(response)
            return response
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
        result = await api_client.delete_source(source_id, token)
        logger.info(f"FRONTEND: Ответ от бэкенда: {result}")
        return {"message": "Source deleted successfully"}
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при удалении источника: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/names", response_class=HTMLResponse)
async def names_list(request: Request, search: Optional[str] = None):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    try:
        names = await api_client.get_names(token)
        if search:
            search_lower = search.lower()
            names = [n for n in names if search_lower in (n['name_ru'] or '').lower() or search_lower in (n['name_en'] or '').lower() or search_lower in (n['name_sanskrit'] or '').lower()]
        return templates.TemplateResponse("names.html", {"request": request, "names": names})
    except Exception as e:
        if "401" in str(e):
            response = RedirectResponse("/login", status_code=303)
            await remove_token(response)
            return response
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load names"
        })

@app.delete("/asana-names/{name_id}")
async def delete_name(name_id: str, request: Request):
    logger.info(f"FRONTEND: Получен запрос на удаление названия: {name_id}")
    token = await get_current_token(request)
    if not token:
        logger.error("FRONTEND: Нет токена авторизации!")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        result = await api_client.delete_name(name_id, token)
        logger.info(f"FRONTEND: Ответ от бэкенда: {result}")
        return {"message": "Name deleted successfully"}
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при удалении названия: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/asana/add", response_class=HTMLResponse)
async def add_asana_form(request: Request):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    try:
        names = await api_client.get_names(token)
        sources = await api_client.get_sources(token)
        return templates.TemplateResponse(
            "add_asana.html",
            {"request": request, "names": names, "sources": sources}
        )
    except Exception as e:
        if "401" in str(e):
            response = RedirectResponse("/login", status_code=303)
            await remove_token(response)
            return response
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Не удалось загрузить данные для формы добавления асаны"
        })

@app.post("/sources")
async def add_source(request: Request):
    token = await get_current_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Не авторизован"})
    try:
        data = await request.json()
        title = data.get("title")
        author = data.get("author")
        year = data.get("year")
        if not (title and author and year):
            return JSONResponse(status_code=400, content={"detail": "Все поля обязательны"})
        result = await api_client.make_request(
            "POST",
            f"{api_client.BACKEND_URL}/sources",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"title": title, "author": author, "year": year}
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

@app.post("/asana-names")
async def add_asana_name(request: Request):
    token = await get_current_token(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Не авторизован"})
    try:
        data = await request.json()
        name_sanskrit = data.get("name_sanskrit")
        name_ru = data.get("name_ru")
        name_en = data.get("name_en")
        if not (name_sanskrit and name_ru and name_en):
            return JSONResponse(status_code=400, content={"detail": "Все поля обязательны"})
        result = await api_client.make_request(
            "POST",
            f"{api_client.BACKEND_URL}/asana-names",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"name_sanskrit": name_sanskrit, "name_ru": name_ru, "name_en": name_en}
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

@app.post("/asana/add", response_class=HTMLResponse)
async def add_asana(request: Request):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    try:
        form = await request.form()
        selected_name = form.get("selected_name")
        new_name_ru = form.get("new_name_ru")
        new_name_en = form.get("new_name_en")
        new_name_sanskrit = form.get("new_name_sanskrit")
        selected_source = form.get("selected_source")
        new_source_title = form.get("new_source_title")
        new_source_author = form.get("new_source_author")
        new_source_year = form.get("new_source_year")
        photo = form.get("photo")
        # Получаем файл
        photo_file = None
        if "photo" in request._form:
            photo_file = request._form["photo"]
        elif hasattr(request, "files"):
            photo_file = request.files.get("photo")
        if not photo_file:
            # Попробуем получить через UploadFile
            try:
                form2 = await request.form()
                photo_file = form2.get("photo")
            except:
                pass
        if not photo_file:
            return templates.TemplateResponse("error.html", {"request": request, "error": "Фотография обязательна"})
        # Читаем файл
        photo_bytes = await photo_file.read()
        # Вызываем api_client
        result = await api_client.add_asana(
            selected_name=selected_name,
            selected_source=selected_source,
            new_name_ru=new_name_ru,
            new_name_en=new_name_en,
            new_name_sanskrit=new_name_sanskrit,
            new_source_title=new_source_title,
            new_source_author=new_source_author,
            new_source_year=new_source_year,
            photo=photo_bytes,
            token=token
        )
        if result.get("success"):
            return RedirectResponse("/asanas", status_code=303)
        else:
            return templates.TemplateResponse("error.html", {"request": request, "error": result.get("data", {}).get("detail", "Ошибка при добавлении асаны")})
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

@app.delete("/asanas")
async def delete_asana(request: Request, uri: str = Query(...)):
    logger.info(f"FRONTEND: Получен запрос на удаление асаны: {uri}")
    token = await get_current_token(request)
    if not token:
        logger.error("FRONTEND: Нет токена авторизации!")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        result = await api_client.delete_asana(uri, token)
        logger.info(f"FRONTEND: Ответ от бэкенда: {result}")
        return {"message": "Asana deleted successfully"}
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при удалении асаны: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/delete-source")
async def delete_source(request: Request, uri: str = Query(...)):
    logger.info(f"FRONTEND: Получен запрос на удаление источника: {uri}")
    token = await get_current_token(request)
    if not token:
        logger.error("FRONTEND: Нет токена авторизации!")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        result = await api_client.delete_source(uri, token)
        logger.info(f"FRONTEND: Ответ от бэкенда: {result}")
        return {"message": "Source deleted successfully"}
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при удалении источника: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/delete-asana-name")
async def delete_asana_name(request: Request, uri: str = Query(...)):
    logger.info(f"FRONTEND: Получен запрос на удаление названия: {uri}")
    token = await get_current_token(request)
    if not token:
        logger.error("FRONTEND: Нет токена авторизации!")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        result = await api_client.delete_name(uri, token)
        logger.info(f"FRONTEND: Ответ от бэкенда: {result}")
        return {"message": "Name deleted successfully"}
    except Exception as e:
        logger.error(f"FRONTEND: Ошибка при удалении названия: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/asana", response_class=HTMLResponse)
async def asana_detail_query(request: Request, id: Optional[str] = Query(None)):
    if not id:
        return RedirectResponse("/asanas")
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    try:
        asanas = await api_client.get_asanas(token)
        asana = next((a for a in asanas if a["id"] == id), None)
        if not asana:
            return templates.TemplateResponse("error.html", {"request": request, "error": "Асана не найдена"})
        return templates.TemplateResponse("asana_detail.html", {"request": request, "asana": asana})
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

@app.post("/asana/{asana_id}/add-photo")
async def add_asana_photo(request: Request, asana_id: str):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    form = await request.form()
    photo_file = form.get("photo")
    if not photo_file:
        return templates.TemplateResponse("error.html", {"request": request, "error": "Файл не выбран"})
    photo_bytes = await photo_file.read()
    # Вызываем api_client для добавления фото (реализуй на бэке)
    try:
        await api_client.add_asana_photo(asana_id, photo_bytes, token)
        return RedirectResponse(f"/asana/{asana_id}", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    return templates.TemplateResponse("settings.html", {"request": request})
