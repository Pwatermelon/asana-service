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

async def get_current_token(request: Request) -> Optional[str]:
    """Get token from encrypted cookie"""
    token_cookie = request.cookies.get("session_token")
    if not token_cookie:
        return None
    
    try:
        # Decode and verify the cookie
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
    
    # Create token data
    token_data = {
        "token": token,
        "expires_at": expires_at
    }
    
    # Encrypt token data
    encrypted_token = jwt.encode(token_data, SECRET_KEY, algorithm="HS256")
    
    # Set secure cookie
    response.set_cookie(
        key="session_token",
        value=encrypted_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=24 * 60 * 60  # 24 hours
    )
    logger.info("Saved token in secure cookie")

async def remove_token(response: Response):
    """Remove token cookie"""
    response.delete_cookie(key="session_token")
    logger.info("Removed token cookie")

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
            response = RedirectResponse("/login", status_code=303)
            await remove_token(response)
            return response
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load asanas. Please try again later."
        })

@app.get("/asana/add", response_class=HTMLResponse)
async def add_asana_page(request: Request):
    token = await get_current_token(request)
    if not token:
        logger.warning(f"Unauthorized access attempt to add asana page from IP: {request.client.host}")
        response = RedirectResponse("/login")
        await remove_token(response)
        return response

    try:
        logger.info("Loading add asana form data")
        sources = await api_client.get_sources(token)
        names = await api_client.get_names(token)
        logger.debug(f"Loaded {len(sources)} sources and {len(names)} names")

        return templates.TemplateResponse("add_asana.html", {
            "request": request,
            "sources": sources,
            "names": names
        })
    except Exception as e:
        logger.error(f"Error loading add asana form data: {str(e)}")
        if "401" in str(e):
            response = RedirectResponse("/login", status_code=303)
            await remove_token(response)
            return response
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load form data. Please try again later."
        })

@app.post("/asana/add", response_class=HTMLResponse)
async def add_asana(request: Request):
    token = await get_current_token(request)
    if not token:
        logger.warning(f"Unauthorized access attempt to add asana from IP: {request.client.host}")
        response = RedirectResponse("/login")
        await remove_token(response)
        return response

    try:
        form = await request.form()
        photo = None
        if "photo" in form:
            photo_file = form["photo"]
            if photo_file.filename:
                photo = await photo_file.read()

        result = await api_client.add_asana(
            selected_name=form.get("selected_name"),
            selected_source=form.get("selected_source"),
            new_name_ru=form.get("new_name_ru"),
            new_name_en=form.get("new_name_en"),
            new_name_sanskrit=form.get("new_name_sanskrit"),
            new_source_title=form.get("new_source_title"),
            new_source_author=form.get("new_source_author"),
            new_source_year=form.get("new_source_year"),
            photo=photo,
            token=token
        )
        
        response = RedirectResponse("/asanas", status_code=303)
        return response

    except ValueError as e:
        logger.error(f"Validation error in add_asana route: {str(e)}")
        if "token is invalid or expired" in str(e).lower():
            response = RedirectResponse("/login", status_code=303)
            await remove_token(response)
            return response
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })
    except Exception as e:
        logger.error(f"Error in add_asana route: {str(e)}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "An unexpected error occurred. Please try again."
        })
