from pydantic import BaseModel, ConfigDict
from datetime import datetime

class SessionFileResponse(BaseModel):
    id: int
    physic_file_id: int
    filename: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)