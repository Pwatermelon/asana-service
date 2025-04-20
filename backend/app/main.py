from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from pydantic import BaseModel
import base64
from app.auth import authenticate_user, create_access_token, get_current_user
from app.ontology import add_asana_name, add_source, load_asana_names, load_asanas, add_asana, load_sources

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
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/asanas")
async def get_asanas(user: str = Depends(get_current_user)):
    return load_asanas()

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
        # Обработка названия
        name_id = None
        if selected_name != "new":
            name_id = selected_name
        elif all([new_name_ru, new_name_en, new_name_sanskrit]):
            name_data = {
                "name_ru": new_name_ru,
                "name_en": new_name_en,
                "name_sanskrit": new_name_sanskrit
            }
            name_id = add_asana_name(name_data)
        else:
            raise HTTPException(status_code=400, detail="При добавлении нового названия все языковые поля обязательны")

        # Обработка источника
        source_id = None
        if selected_source != "new":
            source_id = selected_source
        elif all([new_source_title, new_source_author, new_source_year]):
            source_data = {
                "title": new_source_title,
                "author": new_source_author,
                "year": int(new_source_year)
            }
            source_id = add_source(source_data)
        else:
            raise HTTPException(status_code=400, detail="При добавлении нового источника все поля источника обязательны")

        # Обработка фото
        photo_content = await photo.read()
        photo_base64 = base64.b64encode(photo_content).decode()

        # Добавляем асану
        asana_id = add_asana(name_id=name_id, source_id=source_id, photo_base64=photo_base64)
        return {"message": "Asana added successfully", "id": asana_id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/sources")
async def get_sources(user: str = Depends(get_current_user)):
    return load_sources()

@app.post("/sources")
async def post_source(source: SourceCreate, user: str = Depends(get_current_user)):
    source_id = add_source(source)
    if not source_id:
        raise HTTPException(status_code=400, detail="Source already exists or invalid")
    return {"message": "Source added successfully", "id": source_id}

@app.get("/asana-names")
async def get_asana_names(user: str = Depends(get_current_user)):
    return load_asana_names()

@app.post("/asana-names")
async def post_asana_name(name: AsanaNameCreate, user: str = Depends(get_current_user)):
    name_id = add_asana_name(name)
    if not name_id:
        raise HTTPException(status_code=400, detail="Asana name already exists or invalid")
    return {"message": "Asana name added successfully", "id": name_id}