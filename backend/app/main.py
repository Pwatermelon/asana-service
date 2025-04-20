from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import authenticate_user, create_access_token, get_current_user
from app.ontology import add_asana_name, add_source, load_asana_names, load_asanas, add_asana, load_sources
from app.models import Token

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
async def post_asana(name_ru: str, name_en: str, name_sanskrit: str, photo_base64: str, source: str, user: str = Depends(get_current_user)):
    add_asana(name_ru, name_en, name_sanskrit, photo_base64, source)
    return {"message": "Asana added successfully"}

@app.get("/sources")
async def get_sources(user: str = Depends(get_current_user)):
    return load_sources()

@app.post("/sources")
async def post_source(name: str, user: str = Depends(get_current_user)):
    if not name:
        raise HTTPException(status_code=400, detail="Source name is required")
    if not add_source(name):
        raise HTTPException(status_code=400, detail="Source already exists or invalid")
    return {"message": "Source added successfully"}

@app.get("/asana-names")
async def get_asana_names(user: str = Depends(get_current_user)):
    return load_asana_names()

@app.post("/asana-names")
async def post_asana_name(name: str, user: str = Depends(get_current_user)):
    if not name:
        raise HTTPException(status_code=400, detail="Asana name is required")
    if not add_asana_name(name):
        raise HTTPException(status_code=400, detail="Asana name already exists or invalid")
    return {"message": "Asana name added successfully"}