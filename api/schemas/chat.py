from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any

from api.models.message import Message
from api.schemas.file import SessionFileResponse

class MessageResponse(BaseModel):
    id: int
    chatbox_id: int
    role: str       
    content: str    
    metadata_data: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatBoxResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalRequest(BaseModel):
    action: str  
    edited_args: dict | None = None

    model_config = ConfigDict(from_attributes=True)

class ChatHistoryResponse(BaseModel):
    chatbox_id: int 
    title: str      
    
    messages: list[MessageResponse] = []
    session_files: list[SessionFileResponse] = []
    pending_tools: Optional[list[Any]] = None

    model_config = ConfigDict(from_attributes=True)
