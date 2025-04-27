from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from pydantic import BaseModel
import base64
import logging
from app.auth import authenticate_user, create_access_token, get_current_user
from app.ontology import (
    add_asana_name, add_source, load_asana_names, load_asanas, add_asana, load_sources,
    delete_source_from_ontology, delete_asana_name_from_ontology
)
from app.config import logger

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
    source_id = add_source(source)
    if not source_id:
        logger.warning(f"Failed to add source: {source}")
        raise HTTPException(status_code=400, detail="Source already exists or invalid")
    logger.info(f"Successfully added source with ID: {source_id}")
    return {"message": "Source added successfully", "id": source_id}

@app.delete("/sources/{source_id}")
async def delete_source(source_id: str, user: str = Depends(get_current_user)):
    logger.info(f"Delete source request by user: {user}")
    logger.debug(f"Source ID: {source_id}")
    
    try:
        success = delete_source_from_ontology(source_id)
        if not success:
            logger.warning(f"Source {source_id} not found or could not be deleted")
            raise HTTPException(status_code=404, detail="Source not found")
        logger.info(f"Successfully deleted source {source_id}")
        return {"message": "Source deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting source: {str(e)}")
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
    name_id = add_asana_name(name)
    if not name_id:
        logger.warning(f"Failed to add asana name: {name}")
        raise HTTPException(status_code=400, detail="Asana name already exists or invalid")
    logger.info(f"Successfully added asana name with ID: {name_id}")
    return {"message": "Asana name added successfully", "id": name_id}

@app.delete("/asana-names/{name_id}")
async def delete_asana_name(name_id: str, user: str = Depends(get_current_user)):
    logger.info(f"Delete asana name request by user: {user}")
    logger.debug(f"Name ID: {name_id}")
    
    try:
        success = delete_asana_name_from_ontology(name_id)
        if not success:
            logger.warning(f"Asana name {name_id} not found or could not be deleted")
            raise HTTPException(status_code=404, detail="Asana name not found")
        logger.info(f"Successfully deleted asana name {name_id}")
        return {"message": "Asana name deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting asana name: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))