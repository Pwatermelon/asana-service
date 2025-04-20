from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app import api_client
import logging

logging.basicConfig(level=logging.DEBUG)
app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# сессия по токену
session_tokens = {}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    token = session_tokens.get(request.client.host)
    if token:
        return RedirectResponse("/asanas")
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        token_data = await api_client.login(username, password)
        session_tokens[request.client.host] = token_data["access_token"]
        logging.debug(f"Token stored for {request.client.host}: {token_data['access_token']}")
        return RedirectResponse("/asanas", status_code=303)
    except Exception as e:
        logging.error(f"Login failed: {e}")
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"})

@app.get("/asanas", response_class=HTMLResponse)
async def asanas_list(request: Request):
    token = session_tokens.get(request.client.host)
    logging.debug(f"Token for {request.client.host}: {token}")
    if not token:
        logging.debug(f"Redirecting {request.client.host} to login")
        return RedirectResponse("/login")
    asanas = await api_client.get_asanas(token)
    return templates.TemplateResponse("asana_list.html", {"request": request, "asanas": asanas})

@app.get("/asana/add", response_class=HTMLResponse)
async def add_asana_page(request: Request):
    token = session_tokens.get(request.client.host)
    if not token:
        return RedirectResponse("/login")
    return templates.TemplateResponse("add_asana.html", {"request": request})

@app.post("/asana/add", response_class=HTMLResponse)
async def add_asana(request: Request,
                    name_ru: str = Form(...),
                    name_en: str = Form(...),
                    name_sanskrit: str = Form(...),
                    source: str = Form(...),
                    photo: bytes = Form(...)):
    token = session_tokens.get(request.client.host)
    if not token:
        return RedirectResponse("/login")

    import base64
    photo_base64 = base64.b64encode(photo).decode()

    await api_client.add_asana(name_ru, name_en, name_sanskrit, photo_base64, source, token)
    return RedirectResponse("/asanas", status_code=303)
