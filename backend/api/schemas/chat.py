from pydantic import BaseModel, ConfigDict
from datetime import datetime

# ==========================================
# SCHEMA CHO MESSAGE
# ==========================================
class MessageResponse(BaseModel):
    id: int
    chatbox_id: int
    role: str       # Thường là "user" hoặc "assistant" (bot)
    content: str    # Nội dung tin nhắn
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# SCHEMA CHO CHATBOX
# ==========================================
class ChatBoxResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)