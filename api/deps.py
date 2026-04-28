from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
import jwt

from core.config import settings
from api.schemas.user import User
from api.repositories.user_repo import get_user
from core.postgres import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Khai báo công cụ bóc tách Token. 
# tokenUrl="login" là khai báo cho Swagger UI biết: "Muốn lấy token thì gọi API /login nhé"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db) 
):
    # Định nghĩa sẵn cái lỗi 401 chuẩn OAuth2
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token is expired or invalid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
            
        user_data = await get_user(db, username) 
        if not user_data:
            raise credentials_exception
            
        return user_data

    except jwt.PyJWTError:
        raise credentials_exception

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Account is blocked")
    return current_user