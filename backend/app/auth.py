from __future__ import annotations
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app import config
from app.models import TokenData, User
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

logger = logging.getLogger("asana_service.auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

engine = create_engine(config.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(username: str, password: str):
    logger.debug(f"Attempting to authenticate user: {username}")
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user:
        logger.warning(f"User not found: {username}")
        return False
    if not verify_password(password, user.password_hash):
        logger.warning(f"Invalid password for user: {username}")
        return False
    logger.info(f"Successfully authenticated user: {username}")
    return {"username": user.username}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    logger.debug(f"Creating token for {data.get('sub')} expiring at {expire}")
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.debug("Decoding JWT token")
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Token missing username claim")
            raise credentials_exception
        token_data = TokenData(username=username)
        logger.debug(f"Successfully validated token for user: {username}")
        return token_data.username
    except JWTError as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise credentials_exception
