from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile, Query, Request, Path
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional, List
from pydantic import BaseModel
import base64
import os
import logging
import json
from starlette.responses import RedirectResponse
from app.auth import (
    authenticate_user, create_access_token, get_current_user, is_admin, is_expert_or_admin, 
    register_user, confirm_registration, reset_password_request, reset_password_confirm
)
from app.ontology import (
    add_asana_name, add_source, load_asana_names, load_asanas, add_asana, load_sources,
    delete_source_from_ontology, delete_asana_name_from_ontology, delete_asana_from_ontology, 
    add_photo_to_asana, get_asanas_by_first_letter, get_asanas_by_source, search_asanas_by_name,
    get_photo_of_asana_from_source
)
from app.config import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from app.models import Base, User, Token, UserRegistration, UserLogin, PasswordReset, PasswordResetConfirm, AboutProject, ExpertInstructions
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from app import config
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError
from datetime import datetime

# Create module logger
logger = logging.getLogger("asana_service.api")

# Определение моделей для данных, используемых в API
class AsanaNameCreate(BaseModel):
    name_ru: str
    name_sanskrit: Optional[str] = None
    transliteration: Optional[str] = None
    definition: Optional[str] = None

class SourceCreate(BaseModel):
    title: str
    author: str
    year: int
    publisher: Optional[str] = None
    pages: Optional[int] = None
    annotation: Optional[str] = None

class AsanaCreate(BaseModel):
    selected_name: Optional[str] = None
    new_name: Optional[AsanaNameCreate] = None
    selected_source: Optional[str] = None
    new_source: Optional[SourceCreate] = None
    photo_base64: str

class TextContent(BaseModel):
    content: str

app = FastAPI(
    title=config.APP_NAME,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    contact={"email": config.APP_CONTACT_EMAIL}
)

# Разрешаем CORS для всех источников (для разработки)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine(config.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Создаём пользователя admin:admin123, если его нет
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def create_default_admin():
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin", 
            password_hash=pwd_context.hash("admin123"),
            role="admin",
            is_confirmed=True
        )
        db.add(admin)
        db.commit()
    
    # Создаем записи о проекте и инструкции, если их нет
    if not db.query(AboutProject).first():
        about = AboutProject(content="О проекте каталога асан")
        db.add(about)
        db.commit()
    
    if not db.query(ExpertInstructions).first():
        instructions = ExpertInstructions(content="Инструкция для экспертов")
        db.add(instructions)
        db.commit()
    
    db.close()

create_default_admin()

# Маршруты аутентификации и авторизации
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"Login attempt for user: {form_data.username}")
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]})
    logger.info(f"Successful login for user: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@app.post("/login")
async def login_form(user_login: UserLogin):
    logger.info(f"Login form attempt for user: {user_login.username}")
    user = authenticate_user(user_login.username, user_login.password)
    if not user:
        logger.warning(f"Failed login form attempt for user: {user_login.username}")
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]}, remember_me=user_login.remember_me)
    logger.info(f"Successful login form for user: {user_login.username}")
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@app.post("/register")
async def register(user_data: UserRegistration):
    logger.info(f"Registration attempt for username: {user_data.username}, email: {user_data.email}")
    try:
        result = register_user(
            username=user_data.username,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            password=user_data.password
        )
        logger.info(f"Successfully registered user: {user_data.username}")
        return result
    except HTTPException as e:
        logger.warning(f"Registration failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during registration")

@app.post("/confirm-registration")
async def confirm(code: str):
    logger.info(f"Confirmation attempt with code: {code}")
    try:
        result = confirm_registration(code)
        logger.info(f"Successfully confirmed user: {result['username']}")
        return result
    except HTTPException as e:
        logger.warning(f"Confirmation failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during confirmation: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during confirmation")

@app.post("/reset-password-request")
async def reset_request(reset_data: PasswordReset):
    logger.info(f"Password reset request for email: {reset_data.email}")
    try:
        result = reset_password_request(reset_data.email)
        logger.info(f"Password reset email sent (if email exists)")
        return result
    except Exception as e:
        logger.error(f"Unexpected error during password reset request: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during password reset request")

@app.post("/reset-password-confirm")
async def reset_confirm(reset_data: PasswordResetConfirm):
    logger.info(f"Password reset confirmation attempt with code: {reset_data.code}")
    try:
        result = reset_password_confirm(reset_data.code, reset_data.new_password)
        logger.info(f"Successfully reset password for user: {result['username']}")
        return result
    except HTTPException as e:
        logger.warning(f"Password reset confirmation failed: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during password reset confirmation: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during password reset confirmation")

@app.get("/logout")
async def logout():
    logger.info("User logout")
    response = RedirectResponse(url="/")
    return response

# Маршруты для асан
@app.get("/asanas", tags=["asana"])
async def get_asanas():
    """Получить все асаны (доступно всем)"""
    logger.info("Getting asanas list for all users")
    asanas = load_asanas()
    logger.info(f"Retrieved {len(asanas)} asanas")
    return asanas

@app.get("/asanas/by-letter/{letter}", tags=["asana"])
async def get_asanas_by_letter(letter: str):
    """Получить асаны, начинающиеся с определенной буквы (доступно всем)"""
    logger.info(f"Getting asanas starting with letter: {letter}")
    asanas = get_asanas_by_first_letter(letter)
    return asanas

@app.get("/asanas/by-source/{source_id}", tags=["asana"])
async def get_source_asanas(source_id: str):
    """Получить асаны из определенного источника (доступно всем)"""
    logger.info(f"Getting asanas from source: {source_id}")
    asanas = get_asanas_by_source(source_id)
    return asanas

@app.get("/asanas/search", tags=["asana"])
async def search_asanas(query: str, fuzzy: bool = True):
    """Поиск асан по названию (доступно всем)"""
    logger.info(f"Searching asanas with query: {query}, fuzzy: {fuzzy}")
    if fuzzy:
        asanas = search_asanas_by_name(query)
    else:
        # Простой поиск по подстроке
        all_asanas = load_asanas()
        asanas = [a for a in all_asanas if query.lower() in a["name"]["ru"].lower()]
    
    logger.info(f"Found {len(asanas)} asanas matching query: {query}")
    return asanas

@app.get("/asana/add", tags=["asana"])
def add_asana_page(request: Request):
    """Страница добавления асаны (только для expert/admin)"""
    user_role = get_user_role_from_request(request)
    if user_role not in ['admin', 'expert']:
        return RedirectResponse(url="/login")
    
    # Загружаем существующие названия и источники для выбора
    names = load_asana_names()
    sources = load_sources()
    
    return templates.TemplateResponse(
        "add_asana.html",
        {
            "request": request,
            "names": names,
            "sources": sources,
            "user_role": user_role,
            "is_admin": user_role == 'admin',
            "is_authenticated": True,
            "is_expert_or_admin": True,
            "year": datetime.now().year
        }
    )

@app.post("/asana", tags=["asana"])
async def post_asana(
    selected_name: str = Form(...),
    new_name_ru: Optional[str] = Form(None),
    new_name_sanskrit: Optional[str] = Form(None),
    transliteration: Optional[str] = Form(None),
    definition: Optional[str] = Form(None),
    selected_source: str = Form(...),
    new_source_title: Optional[str] = Form(None),
    new_source_author: Optional[str] = Form(None),
    new_source_year: Optional[int] = Form(None),
    new_source_publisher: Optional[str] = Form(None),
    new_source_pages: Optional[int] = Form(None),
    new_source_annotation: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    user: str = Depends(is_expert_or_admin)
):
    """Добавить новую асану (только эксперты и админы)"""
    try:
        logger.info(f"Adding new asana by user: {user}")
        logger.debug(f"Form data received - selected_name: {selected_name}, selected_source: {selected_source}")
        logger.debug(f"New name data: ru={new_name_ru}, sanskrit={new_name_sanskrit}")
        logger.debug(f"New source data: title={new_source_title}, author={new_source_author}, year={new_source_year}")
        logger.debug(f"Photo filename: {photo.filename}")
        
        # Обработка названия
        name_id = None
        if selected_name != "new":
            logger.debug(f"Using existing name ID: {selected_name}")
            name_id = selected_name
        elif new_name_ru:
            logger.info("Creating new asana name")
            name_data = {
                "name_ru": new_name_ru
            }
            if new_name_sanskrit:
                name_data["name_sanskrit"] = new_name_sanskrit
            if transliteration:
                name_data["transliteration"] = transliteration
            if definition:
                name_data["definition"] = definition
            name_id = add_asana_name(name_data)
            logger.debug(f"Created new name with ID: {name_id}")
        else:
            logger.error("Missing required name fields for new name")
            raise HTTPException(status_code=400, detail="При добавлении нового названия поле названия на русском обязательно")

        # Обработка источника
        source_id = None
        if selected_source != "new":
            logger.debug(f"Using existing source ID: {selected_source}")
            source_id = selected_source
        elif all([new_source_title, new_source_author, new_source_year]):
            logger.info("Creating new source")
            source_data = {
                "title": new_source_title,
                "author": new_source_author,
                "year": int(new_source_year)
            }
            
            # Добавляем необязательные поля, если они есть
            if new_source_publisher:
                source_data["publisher"] = new_source_publisher
            if new_source_pages:
                source_data["pages"] = int(new_source_pages)
            if new_source_annotation:
                source_data["annotation"] = new_source_annotation
                
            source_id = add_source(source_data)
            logger.debug(f"Created new source with ID: {source_id}")
        else:
            logger.error("Missing required source fields for new source")
            raise HTTPException(status_code=400, detail="При добавлении нового источника поля автора, названия и года обязательны")

        # Обработка фото
        logger.info("Processing photo upload")
        photo_content = await photo.read()
        photo_base64 = base64.b64encode(photo_content).decode()
        logger.debug(f"Photo size in bytes: {len(photo_content)}")

        # Добавляем асану
        logger.info("Adding asana to ontology")
        asana_id = add_asana(name_id=name_id, source_id=source_id, photo_base64=photo_base64)
        logger.info(f"Successfully created asana with ID: {asana_id}")
        
        return {"message": "Asana added successfully", "id": asana_id}
    except Exception as e:
        logger.error(f"Error adding asana: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/asanas")
async def delete_asana(user: str = Depends(is_expert_or_admin), uri: str = Query(...)):
    """Удалить асану (только эксперты и админы)"""
    try:
        logger.info(f"Deleting asana with URI: {uri} by user: {user}")
        success = delete_asana_from_ontology(uri)
        if not success:
            logger.warning(f"Asana not found: {uri}")
            raise HTTPException(status_code=404, detail="Asana not found")
        logger.info(f"Successfully deleted asana: {uri}")
        return {"message": "Asana deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting asana: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/asana/{asana_id}/add-photo")
async def add_asana_photo_endpoint(
    asana_id: str, 
    source_id: str = Form(...),
    photos: List[UploadFile] = File(...), 
    user: str = Depends(is_expert_or_admin)
):
    """Добавить фото к асане (только эксперты и админы)"""
    try:
        results = []
        for photo in photos:
            photo_bytes = await photo.read()
            photo_uri = add_photo_to_asana(asana_id, photo_bytes, source_id)
            results.append(photo_uri)
        return {"message": "Фото добавлены", "photo_ids": results}
    except Exception as e:
        logger.error(f"Error adding photo to asana: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Маршруты для источников
@app.get("/sources")
async def get_sources():
    """Получить все источники (доступно всем)"""
    logger.info("Getting sources list for all users")
    sources = load_sources()
    logger.info(f"Retrieved {len(sources)} sources")
    return sources

@app.post("/sources")
async def post_source(source: SourceCreate, user: str = Depends(is_expert_or_admin)):
    """Добавить новый источник (только эксперты и админы)"""
    logger.info(f"Adding new source by user: {user}")
    try:
        source_id = add_source(source.dict())
        if not source_id:
            logger.warning(f"Failed to add source: {source}")
            raise HTTPException(status_code=400, detail="Source already exists or invalid")
        logger.info(f"Successfully added source with ID: {source_id}")
        return {"message": "Source added successfully", "id": source_id}
    except Exception as e:
        logger.error(f"Error adding source: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/delete-source")
@app.delete("/delete-source/")
async def delete_source(user: str = Depends(is_expert_or_admin), uri: str = Query(...)):
    """Удалить источник (только эксперты и админы)"""
    logger.info(f"Deleting source with URI: {uri} by user: {user}")
    try:
        success = delete_source_from_ontology(uri)
        if not success:
            logger.warning(f"Source not found: {uri}")
            raise HTTPException(status_code=404, detail="Source not found")
        logger.info(f"Successfully deleted source: {uri}")
        return {"message": "Source deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting source: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Маршруты для названий асан
@app.get("/asana-names")
async def get_asana_names():
    """Получить все названия асан (доступно всем)"""
    logger.info("Getting asana names list for all users")
    names = load_asana_names()
    logger.info(f"Retrieved {len(names)} asana names")
    return names

@app.post("/asana-names")
async def post_asana_name(name: AsanaNameCreate, user: str = Depends(is_expert_or_admin)):
    """Добавить новое название асаны (только эксперты и админы)"""
    logger.info(f"Adding new asana name by user: {user}")
    try:
        name_id = add_asana_name(name.dict())
        if not name_id:
            logger.warning(f"Failed to add asana name: {name}")
            raise HTTPException(status_code=400, detail="Asana name already exists or invalid")
        logger.info(f"Successfully added asana name with ID: {name_id}")
        return {"message": "Asana name added successfully", "id": name_id}
    except Exception as e:
        logger.error(f"Error adding asana name: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/delete-asana-name")
@app.delete("/delete-asana-name/")
async def delete_asana_name(user: str = Depends(is_expert_or_admin), uri: str = Query(...)):
    """Удалить название асаны (только эксперты и админы)"""
    logger.info(f"Deleting asana name with URI: {uri} by user: {user}")
    try:
        success = delete_asana_name_from_ontology(uri)
        if not success:
            logger.warning(f"Asana name not found: {uri}")
            raise HTTPException(status_code=404, detail="Asana name not found")
        logger.info(f"Successfully deleted asana name: {uri}")
        return {"message": "Asana name deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting asana name: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Маршруты для информации о проекте и инструкций
@app.get("/about-project")
async def get_about_project():
    """Получить информацию о проекте (доступно всем)"""
    logger.info("Getting about project info")
    db = SessionLocal()
    about = db.query(AboutProject).first()
    db.close()
    if not about:
        return {"content": "Информация о проекте отсутствует"}
    return {"content": about.content}

@app.post("/about-project")
async def update_about_project(data: TextContent, user: str = Depends(is_admin)):
    """Обновить информацию о проекте (только админ)"""
    logger.info(f"Updating about project info by user: {user}")
    db = SessionLocal()
    about = db.query(AboutProject).first()
    if not about:
        about = AboutProject(content=data.content)
        db.add(about)
    else:
        about.content = data.content
    db.commit()
    db.close()
    return {"message": "About project info updated successfully"}

@app.get("/expert-instructions")
async def get_expert_instructions():
    """Получить инструкции для экспертов (доступно всем)"""
    logger.info("Getting expert instructions")
    db = SessionLocal()
    instructions = db.query(ExpertInstructions).first()
    db.close()
    if not instructions:
        return {"content": "Инструкции для экспертов отсутствуют"}
    return {"content": instructions.content}

@app.post("/expert-instructions")
async def update_expert_instructions(data: TextContent, user: str = Depends(is_admin)):
    """Обновить инструкции для экспертов (только админ)"""
    logger.info(f"Updating expert instructions by user: {user}")
    db = SessionLocal()
    instructions = db.query(ExpertInstructions).first()
    if not instructions:
        instructions = ExpertInstructions(content=data.content)
        db.add(instructions)
    else:
        instructions.content = data.content
    db.commit()
    db.close()
    return {"message": "Expert instructions updated successfully"}

# Маршрут для скачивания/загрузки онтологии
@app.get("/download-ontology")
async def download_ontology():
    """Скачать файл онтологии (доступно всем)"""
    logger.info("Downloading ontology file")
    if not os.path.exists(config.OWL_FILE_PATH):
        logger.error("Ontology file not found")
        raise HTTPException(status_code=404, detail="Файл онтологии не найден")
    logger.info("Ontology file found, sending to client")
    return FileResponse(
        path=config.OWL_FILE_PATH,
        filename="asana_ontology.owl",
        media_type="application/rdf+xml"
    )

@app.post("/upload-ontology")
async def upload_ontology(ontology_file: UploadFile = File(...), user: str = Depends(is_admin)):
    """Загрузить файл онтологии (только админ)"""
    logger.info(f"Uploading ontology file by user: {user}")
    try:
        content = await ontology_file.read()
        with open(config.OWL_FILE_PATH, "wb") as f:
            f.write(content)
        logger.info("Ontology file uploaded successfully")
        return {"message": "Ontology file uploaded successfully"}
    except Exception as e:
        logger.error(f"Error uploading ontology file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error uploading ontology file: {str(e)}")

@app.get("/asana/{asana_id}/photo-by-source/{source_id}")
async def get_asana_photo_by_source(asana_id: str, source_id: str):
    """
    Получить фото асаны из конкретного источника (если есть)
    """
    photo = get_photo_of_asana_from_source(asana_id, source_id)
    if photo:
        return {"photo": photo}
    return {"photo": None}

templates = Jinja2Templates(directory="frontend/app/templates")

def get_user_role_from_request(request: Request) -> str:
    token = request.cookies.get('access_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return 'guest'
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload.get('role', 'guest')
    except JWTError:
        return 'guest'

def get_asana_by_id(asana_id: str):
    asanas = load_asanas()
    for asana in asanas:
        if asana["id"] == asana_id:
            return asana
    return None

@app.get("/asanas-page")
def asanas_page(request: Request, search_query: str = '', current_letter: str = ''):
    asanas = load_asanas()
    grouped_asanas = {}  # группировка по буквам
    for asana in asanas:
        first_letter = asana["name"]["ru"][0].upper() if asana["name"]["ru"] else "?"
        grouped_asanas.setdefault(first_letter, []).append(asana)
    
    # Получаем роль пользователя
    user_role = get_user_role_from_request(request)
    is_authenticated = user_role != 'guest'
    is_expert_or_admin = user_role in ['admin', 'expert']
    
    return templates.TemplateResponse(
        "asana_list.html",
        {
            "request": request,
            "grouped_asanas": grouped_asanas,
            "search_query": search_query,
            "current_letter": current_letter,
            "user_role": user_role,
            "is_authenticated": is_authenticated,
            "is_expert_or_admin": is_expert_or_admin,
            "is_admin": user_role == 'admin'
        }
    )

@app.get("/asana/{asana_id}-page", tags=["asana"])
def asana_detail_page(request: Request, asana_id: str = Path(...)):
    asana = get_asana_by_id(asana_id)
    sources = load_sources()
    return templates.TemplateResponse(
        "asana_detail.html",
        {
            "request": request,
            "asana": asana,
            "sources": sources,
            "user_role": get_user_role_from_request(request)
        }
    )

@app.get("/sources-page")
def sources_page(request: Request):
    sources = load_sources()
    return templates.TemplateResponse("sources.html", {"request": request, "sources": sources, "user_role": get_user_role_from_request(request)})

@app.get("/settings-page")
def settings_page(request: Request):
    user_role = get_user_role_from_request(request)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user_role": user_role,
            "is_admin": user_role == 'admin',
            "is_authenticated": user_role != 'guest',
            "is_expert_or_admin": user_role in ['admin', 'expert'],
        }
    )

@app.get("/about-page")
def about_page(request: Request):
    db = SessionLocal()
    about = db.query(AboutProject).first()
    db.close()
    content = about.content if about else "Информация о проекте отсутствует"
    
    # Получаем роль пользователя
    user_role = get_user_role_from_request(request)
    is_authenticated = user_role != 'guest'
    is_expert_or_admin = user_role in ['admin', 'expert']
    
    return templates.TemplateResponse(
        "about_project.html", 
        {
            "request": request, 
            "content": content, 
            "user_role": user_role,
            "is_authenticated": is_authenticated,
            "is_expert_or_admin": is_expert_or_admin,
            "is_admin": user_role == 'admin'
        }
    )

@app.get("/expert-instructions-page")
def expert_instructions_page(request: Request):
    db = SessionLocal()
    instructions = db.query(ExpertInstructions).first()
    db.close()
    content = instructions.content if instructions else "Инструкции для экспертов отсутствуют"
    return templates.TemplateResponse("expert_instructions.html", {"request": request, "content": content, "user_role": get_user_role_from_request(request)})

@app.get("/sources/add")
def add_source_page(request: Request):
    """Страница добавления источника (только для expert/admin)"""
    user_role = get_user_role_from_request(request)
    if user_role not in ['admin', 'expert']:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        "add_source.html",
        {
            "request": request,
            "user_role": user_role,
            "is_admin": user_role == 'admin',
            "is_authenticated": True,
            "is_expert_or_admin": True,
            "year": datetime.now().year
        }
    )

# API routes
@app.get("/api/asanas/search")
async def api_search_asanas(query: str, fuzzy: bool = True):
    """API: Поиск асан по названию"""
    logger.info(f"API: Searching asanas with query: {query}, fuzzy: {fuzzy}")
    if fuzzy:
        asanas = search_asanas_by_name(query)
    else:
        all_asanas = load_asanas()
        asanas = [a for a in all_asanas if query.lower() in a["name"]["ru"].lower()]
    return asanas

@app.post("/api/asana")
async def api_post_asana(
    selected_name: str = Form(...),
    new_name_ru: Optional[str] = Form(None),
    new_name_sanskrit: Optional[str] = Form(None),
    transliteration: Optional[str] = Form(None),
    definition: Optional[str] = Form(None),
    selected_source: str = Form(...),
    new_source_title: Optional[str] = Form(None),
    new_source_author: Optional[str] = Form(None),
    new_source_year: Optional[int] = Form(None),
    new_source_publisher: Optional[str] = Form(None),
    new_source_pages: Optional[int] = Form(None),
    new_source_annotation: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    user: str = Depends(is_expert_or_admin)
):
    """API: Добавить новую асану"""
    try:
        logger.info(f"API: Adding new asana by user: {user}")
        logger.debug(f"Form data received - selected_name: {selected_name}, selected_source: {selected_source}")
        logger.debug(f"New name data: ru={new_name_ru}, sanskrit={new_name_sanskrit}")
        logger.debug(f"New source data: title={new_source_title}, author={new_source_author}, year={new_source_year}")
        logger.debug(f"Photo filename: {photo.filename}")
        
        # Обработка названия
        name_id = None
        if selected_name != "new":
            logger.debug(f"Using existing name ID: {selected_name}")
            name_id = selected_name
        elif new_name_ru:
            logger.info("Creating new asana name")
            name_data = {
                "name_ru": new_name_ru
            }
            if new_name_sanskrit:
                name_data["name_sanskrit"] = new_name_sanskrit
            if transliteration:
                name_data["transliteration"] = transliteration
            if definition:
                name_data["definition"] = definition
            name_id = add_asana_name(name_data)
            logger.debug(f"Created new name with ID: {name_id}")
        else:
            logger.error("Missing required name fields for new name")
            raise HTTPException(status_code=400, detail="При добавлении нового названия поле названия на русском обязательно")

        # Обработка источника
        source_id = None
        if selected_source != "new":
            logger.debug(f"Using existing source ID: {selected_source}")
            source_id = selected_source
        elif all([new_source_title, new_source_author, new_source_year]):
            logger.info("Creating new source")
            source_data = {
                "title": new_source_title,
                "author": new_source_author,
                "year": int(new_source_year)
            }
            
            # Добавляем необязательные поля, если они есть
            if new_source_publisher:
                source_data["publisher"] = new_source_publisher
            if new_source_pages:
                source_data["pages"] = int(new_source_pages)
            if new_source_annotation:
                source_data["annotation"] = new_source_annotation
                
            source_id = add_source(source_data)
            logger.debug(f"Created new source with ID: {source_id}")
        else:
            logger.error("Missing required source fields for new source")
            raise HTTPException(status_code=400, detail="При добавлении нового источника поля автора, названия и года обязательны")

        # Обработка фото
        logger.info("Processing photo upload")
        photo_content = await photo.read()
        photo_base64 = base64.b64encode(photo_content).decode()
        logger.debug(f"Photo size in bytes: {len(photo_content)}")

        # Добавляем асану
        logger.info("Adding asana to ontology")
        asana_id = add_asana(name_id=name_id, source_id=source_id, photo_base64=photo_base64)
        logger.info(f"Successfully created asana with ID: {asana_id}")
        
        return {"message": "Asana added successfully", "id": asana_id}
    except Exception as e:
        logger.error(f"Error adding asana: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))