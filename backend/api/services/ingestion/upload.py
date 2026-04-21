from core.minio import s3_client
from core.config import settings
from api.enums.file_status import FileStatus

from api.models.physic_file import PhysicFile
from api.models.session_file import SessionFile

import hashlib
import os
from sqlalchemy.orm import Session


def calculate_file_hash(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def upload_to_s3(file_path: str, 
                unique_filename: str, 
                original_filename: str, 
                chatbox_id: int, 
                content_type: str, 
                file_size: int,
                db: Session):
    try:
        print("="*100)
        print(f"Chatbox id là: {chatbox_id}")
        print("="*100)
        file_hash = calculate_file_hash(file_path)
        physic_file = db.query(PhysicFile).filter(PhysicFile.file_hash == file_hash).first()

        if not physic_file:
            s3_path = f"raw/{original_filename}"
            s3_client.upload_file(
                Filename=file_path,
                Bucket=settings.upload_bucket,
                Key=s3_path
            )

            physic_file = PhysicFile(
                file_hash=file_hash,
                s3_path=s3_path,
                file_size=file_size,
                mime_type=content_type
            )

            db.add(physic_file)
            db.flush()
            print("Đã upload file mới")
        else:
            print("File vật lý đã upload rồi")

        exist_session_file = db.query(SessionFile).filter(SessionFile.chatbox_id == chatbox_id,
                                                    SessionFile.physic_file_id == physic_file.id).first()
        if not exist_session_file:
            session_file = SessionFile(
                chatbox_id=chatbox_id,
                physic_file_id=physic_file.id,
                filename=unique_filename,
                status=FileStatus.PENDING.value
            )

            db.add(session_file)
            db.flush()
            print("Đã upload session file mới")
        else:
            print("Box này có file này rồi")

        return {"status": "Success", "file": original_filename}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)