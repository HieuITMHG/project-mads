from pydantic import BaseModel, ConfigDict
from datetime import datetime
from api.models.user import User

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
