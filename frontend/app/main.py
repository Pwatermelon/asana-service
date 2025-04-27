from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Cookie, Response
from fastapi.responses import RedirectResponse, HTMLResponse
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
async def asanas_list(request: Request):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    
    try:
        asanas = await api_client.get_asanas(token)
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
async def sources_list(request: Request):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    
    try:
        sources = await api_client.get_sources(token)
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
    token = await get_current_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        await api_client.delete_source(source_id, token)
        return {"message": "Source deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/names", response_class=HTMLResponse)
async def names_list(request: Request):
    token = await get_current_token(request)
    if not token:
        return RedirectResponse("/login")
    
    try:
        names = await api_client.get_names(token)
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
    token = await get_current_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        await api_client.delete_name(name_id, token)
        return {"message": "Name deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Existing routes remain unchanged...
