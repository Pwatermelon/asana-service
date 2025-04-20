from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app import api_client

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Сессия по токену
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
        return RedirectResponse("/asanas", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid login"})

@app.get("/logout")
async def logout(request: Request):
    if request.client.host in session_tokens:
        del session_tokens[request.client.host]
    return RedirectResponse("/login", status_code=303)

@app.get("/asanas", response_class=HTMLResponse)
async def asanas_list(request: Request):
    token = session_tokens.get(request.client.host)
    if not token:
        return RedirectResponse("/login")
    asanas = await api_client.get_asanas(token)
    return templates.TemplateResponse("asana_list.html", {"request": request, "asanas": asanas})

@app.get("/asana/add", response_class=HTMLResponse)
async def add_asana_page(request: Request):
    token = session_tokens.get(request.client.host)
    if not token:
        return RedirectResponse("/login")

    # НОВОЕ: получить существующие источники и названия
    sources = await api_client.get_sources(token)
    names = await api_client.get_names(token)

    return templates.TemplateResponse("add_asana.html", {
        "request": request,
        "sources": sources,
        "names": names,
    })

@app.post("/asana/add", response_class=HTMLResponse)
async def add_asana(request: Request,
                    selected_source: str = Form(...),
                    new_source: str = Form(None),
                    selected_name_ru: str = Form(...),
                    new_name_ru: str = Form(None),
                    selected_name_en: str = Form(...),
                    new_name_en: str = Form(None),
                    selected_name_sanskrit: str = Form(...),
                    new_name_sanskrit: str = Form(None),
                    photo: bytes = Form(...)):
    token = session_tokens.get(request.client.host)
    if not token:
        return RedirectResponse("/login")

    import base64
    photo_base64 = base64.b64encode(photo).decode()

    # Определяем что использовать: новое значение или выбранное
    source = new_source if new_source else selected_source
    name_ru = new_name_ru if new_name_ru else selected_name_ru
    name_en = new_name_en if new_name_en else selected_name_en
    name_sanskrit = new_name_sanskrit if new_name_sanskrit else selected_name_sanskrit

    await api_client.add_asana(name_ru, name_en, name_sanskrit, photo_base64, source, token)
    return RedirectResponse("/asanas", status_code=303)
