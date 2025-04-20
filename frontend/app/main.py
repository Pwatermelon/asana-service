from fastapi import FastAPI, Request, Form, File, UploadFile, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Optional
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
async def add_asana(
    request: Request,
    selected_name: str = Form(...),
    new_name_ru: Optional[str] = Form(default=None),
    new_name_en: Optional[str] = Form(default=None),
    new_name_sanskrit: Optional[str] = Form(default=None),
    selected_source: str = Form(...),
    new_source_title: Optional[str] = Form(default=None),
    new_source_author: Optional[str] = Form(default=None),
    new_source_year: Optional[int] = Form(default=None),
    photo: UploadFile = File(...)
):
    token = session_tokens.get(request.client.host)
    if not token:
        return RedirectResponse("/login")

    try:
        # Читаем содержимое файла
        photo_content = await photo.read()
        
        # Validate form data
        if selected_name == "new" and not all([new_name_ru, new_name_en, new_name_sanskrit]):
            raise ValueError("При добавлении нового названия все языковые поля обязательны")
            
        if selected_source == "new" and not all([new_source_title, new_source_author, new_source_year]):
            raise ValueError("При добавлении нового источника все поля источника обязательны")
        
        # Отправляем данные через API клиент
        await api_client.add_asana(
            selected_name=selected_name,
            new_name_ru=new_name_ru,
            new_name_en=new_name_en,
            new_name_sanskrit=new_name_sanskrit,
            selected_source=selected_source,
            new_source_title=new_source_title,
            new_source_author=new_source_author,
            new_source_year=new_source_year,
            photo=photo_content,
            token=token
        )
        return RedirectResponse("/asanas", status_code=303)
    except Exception as e:
        # В случае ошибки возвращаем на форму с сообщением об ошибке
        sources = await api_client.get_sources(token)
        names = await api_client.get_names(token)
        return templates.TemplateResponse("add_asana.html", {
            "request": request,
            "sources": sources,
            "names": names,
            "error": str(e)
        })
