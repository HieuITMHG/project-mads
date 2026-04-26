from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from api.deps import get_current_active_user
from api.models.user import User
from typing import Annotated
from core.config import settings
from api.tasks.ingestion import ingest_upload_file
from pathlib import Path
import uuid
import shutil

UPLOAD_DIR = Path(settings.temp_dir)


router = APIRouter(prefix="/doc", tags=["Doc"])

@router.post("/")
async def upload_doc(file: Annotated[UploadFile, File(description="Upload file from client")], 
                     chatbox_id: Annotated[int, Form(description="Chat box id")],
                     current_user: User = Depends(get_current_active_user)):
    
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    file_size = file.size
    if file_size and file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File tooo large, max upload size is {settings.max_upload_size_mb}MB."
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_file_path = UPLOAD_DIR / unique_filename

    try:
        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.close
    
    task = ingest_upload_file.delay(
        temp_path = str(temp_file_path),
        unique_filename = unique_filename,
        content_type = file.content_type,
        original_filename = file.filename,
        chatbox_id = chatbox_id,
        user_id = current_user.id,
        file_size = file_size
    )
    
    return {
        "task_id": task.id,
        "filename": file.filename,
        "chatbox_id": chatbox_id,
        "status": "Processing"
    }