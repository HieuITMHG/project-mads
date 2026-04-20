from fastapi import APIRouter, Depends, File, UploadFile
from api.deps import get_current_active_user
from api.models.user import User

from api.models.physic_file import PhysicFile
from api.models.session_file import SessionFile

from core.minio import s3_client
from core.config import settings

from typing import Annotated

router = APIRouter(prefix="/doc", tags=["Doc"])

@router.post("/")
async def upload_doc(file: Annotated[UploadFile, File(description="Upload file from client")], 
                     current_user: User = Depends(get_current_active_user)):
    
    await file.seek(0)

    s3_client.upload_fileobj(
        Fileobj=file.file,
        Bucket=settings.upload_bucket,
        Key=f"raw/{file.filename}",
        ExtraArgs = {
            "ContentType": file.content_type
        }
    )

    return {
        "filename": file.filename,
        "content_type": file.content_type,
    }
    