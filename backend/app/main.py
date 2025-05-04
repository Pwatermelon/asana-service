from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile, Query
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from pydantic import BaseModel
import base64
import logging
from app.auth import authenticate_user, create_access_token, get_current_user
from app.ontology import (
    add_asana_name, add_source, load_asana_names, load_asanas, add_asana, load_sources,
    delete_source_from_ontology, delete_asana_name_from_ontology, delete_asana_from_ontology, add_photo_to_asana
)
from app.config import logger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.models import Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from app import config

# Create module logger
logger = logging.getLogger("asana_service.api")

class Token(BaseModel):
    access_token: str
    token_type: str

class AsanaNameCreate(BaseModel):
    name_ru: str
    name_en: str
    name_sanskrit: str

class SourceCreate(BaseModel):
    title: str
    author: str
    year: int

class AsanaCreate(BaseModel):
    selected_name: Optional[str] = None
    new_name: Optional[AsanaNameCreate] = None
    selected_source: Optional[str] = None
    new_source: Optional[SourceCreate] = None
    photo_base64: str

app = FastAPI()

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
        admin = User(username="admin", password_hash=pwd_context.hash("admin123"))
        db.add(admin)
        db.commit()
    db.close()
create_default_admin()

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.info(f"Login attempt for user: {form_data.username}")
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]})
    logger.info(f"Successful login for user: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/asanas")
async def get_asanas(user: str = Depends(get_current_user)):
    logger.info(f"Getting asanas list for user: {user}")
    asanas = load_asanas()
    logger.info(f"Retrieved {len(asanas)} asanas")
    return asanas

@app.post("/asana")
async def post_asana(
    selected_name: str = Form(...),
    new_name_ru: Optional[str] = Form(None),
    new_name_en: Optional[str] = Form(None),
    new_name_sanskrit: Optional[str] = Form(None),
    selected_source: str = Form(...),
    new_source_title: Optional[str] = Form(None),
    new_source_author: Optional[str] = Form(None),
    new_source_year: Optional[int] = Form(None),
    photo: UploadFile = File(...),
    user: str = Depends(get_current_user)
):
    try:
        logger.info(f"Adding new asana by user: {user}")
        logger.debug(f"Form data received - selected_name: {selected_name}, selected_source: {selected_source}")
        logger.debug(f"New name data: ru={new_name_ru}, en={new_name_en}, sanskrit={new_name_sanskrit}")
        logger.debug(f"New source data: title={new_source_title}, author={new_source_author}, year={new_source_year}")
        logger.debug(f"Photo filename: {photo.filename}")
        
        # Обработка названия
        name_id = None
        if selected_name != "new":
            logger.debug(f"Using existing name ID: {selected_name}")
            name_id = selected_name
        elif all([new_name_ru, new_name_en, new_name_sanskrit]):
            logger.info("Creating new asana name")
            name_data = {
                "name_ru": new_name_ru,
                "name_en": new_name_en,
                "name_sanskrit": new_name_sanskrit
            }
            name_id = add_asana_name(name_data)
            logger.debug(f"Created new name with ID: {name_id}")
        else:
            logger.error("Missing required name fields for new name")
            raise HTTPException(status_code=400, detail="При добавлении нового названия все языковые поля обязательны")

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
            source_id = add_source(source_data)
            logger.debug(f"Created new source with ID: {source_id}")
        else:
            logger.error("Missing required source fields for new source")
            raise HTTPException(status_code=400, detail="При добавлении нового источника все поля источника обязательны")

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
        logger.error(f"Error adding asana: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/sources")
async def get_sources(user: str = Depends(get_current_user)):
    logger.info(f"Getting sources list for user: {user}")
    sources = load_sources()
    logger.info(f"Retrieved {len(sources)} sources")
    return sources

@app.post("/sources")
async def post_source(source: SourceCreate, user: str = Depends(get_current_user)):
    logger.info(f"Adding new source by user: {user}")
    source_id = add_source(source.dict())
    if not source_id:
        logger.warning(f"Failed to add source: {source}")
        raise HTTPException(status_code=400, detail="Source already exists or invalid")
    logger.info(f"Successfully added source with ID: {source_id}")
    return {"message": "Source added successfully", "id": source_id}

@app.delete("/delete-source")
@app.delete("/delete-source/")
async def delete_source(user: str = Depends(get_current_user), uri: str = Query(...)):
    print(f"[DEBUG] DELETE /delete-source — uri: {uri}")
    try:
        success = delete_source_from_ontology(uri)
        print(f"[DEBUG] Удаление источника: {success}")
        if not success:
            print(f"[DEBUG] Источник не найден: {uri}")
            raise HTTPException(status_code=404, detail="Source not found")
        return {"message": "Source deleted successfully"}
    except Exception as e:
        print(f"[DEBUG] Ошибка при удалении источника: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/asana-names")
async def get_asana_names(user: str = Depends(get_current_user)):
    logger.info(f"Getting asana names list for user: {user}")
    names = load_asana_names()
    logger.info(f"Retrieved {len(names)} asana names")
    return names

@app.post("/asana-names")
async def post_asana_name(name: AsanaNameCreate, user: str = Depends(get_current_user)):
    logger.info(f"Adding new asana name by user: {user}")
    name_id = add_asana_name(name.dict())
    if not name_id:
        logger.warning(f"Failed to add asana name: {name}")
        raise HTTPException(status_code=400, detail="Asana name already exists or invalid")
    logger.info(f"Successfully added asana name with ID: {name_id}")
    return {"message": "Asana name added successfully", "id": name_id}

@app.delete("/delete-asana-name")
@app.delete("/delete-asana-name/")
async def delete_asana_name(user: str = Depends(get_current_user), uri: str = Query(...)):
    print(f"[DEBUG] DELETE /delete-asana-name — uri: {uri}")
    try:
        success = delete_asana_name_from_ontology(uri)
        print(f"[DEBUG] Удаление названия: {success}")
        if not success:
            print(f"[DEBUG] Название не найдено: {uri}")
            raise HTTPException(status_code=404, detail="Asana name not found")
        return {"message": "Asana name deleted successfully"}
    except Exception as e:
        print(f"[DEBUG] Ошибка при удалении названия: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/asanas")
async def delete_asana(user: str = Depends(get_current_user), uri: str = Query(...)):
    try:
        success = delete_asana_from_ontology(uri)
        if not success:
            raise HTTPException(status_code=404, detail="Asana not found")
        return {"message": "Asana deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/asana/{asana_id}/add-photo")
async def add_asana_photo_backend(asana_id: str, photo: UploadFile = File(...), user: str = Depends(get_current_user)):
    try:
        photo_bytes = await photo.read()
        add_photo_to_asana(asana_id, photo_bytes)
        return {"message": "Фото добавлено"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download-ontology")
async def download_ontology():
    """Позволяет скачать файл онтологии OWL"""
    if not os.path.exists(config.OWL_FILE_PATH):
        raise HTTPException(status_code=404, detail="Файл онтологии не найден")
    return FileResponse(
        path=config.OWL_FILE_PATH,
        filename="asana_ontology.owl",
        media_type="application/rdf+xml"
    )