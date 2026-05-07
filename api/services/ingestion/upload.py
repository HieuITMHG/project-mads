from core.minio import s3_client
from core.config import settings
from api.enums.file_status import FileStatus
from api.enums.file_type import FileType

from api.models.physic_file import PhysicFile
from api.models.session_file import SessionFile

import hashlib
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import pandas as pd

def extract_metadata_from_path(file_path: str, mime_type: str, filename: str) -> dict | None:

    valid_mime_types = [
        "text/csv", 
        "application/vnd.ms-excel", 
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    
    is_spreadsheet = mime_type in valid_mime_types or filename.lower().endswith((".csv", ".xls", ".xlsx"))
    
    if not is_spreadsheet:
        return None

    try:
        if filename.lower().endswith(".csv") or mime_type == "text/csv":
            try:
                df = pd.read_csv(file_path, nrows=2)
            except Exception:
                df = pd.read_csv(file_path, nrows=2, encoding='latin1', sep=None, engine='python')
        else:
            df = pd.read_excel(file_path, nrows=2)

        def serialize_sample(val):
            if pd.isna(val): return None
            if hasattr(val, 'isoformat'): return val.isoformat()
            return val

        sample_data = [
            {k: serialize_sample(v) for k, v in row.items()} 
            for row in df.head(2).to_dict(orient="records")
        ]

        return {
            "type": "spreadsheet",
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample_data": sample_data
        }
    except Exception as e:
        print(f"Lỗi trích xuất metadata từ {file_path}: {e}")
        return None


def calculate_file_hash(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def upload_to_s3(file_path: str, 
                unique_filename: str, 
                original_filename: str, 
                chatbox_id: int, 
                content_type: str, 
                file_size: int,
                db: AsyncSession):
    try:
        is_physic_exist = False
        sessionfile_id = 0
        file_hash = calculate_file_hash(file_path)
        req_physic = await db.execute(select(PhysicFile).filter(PhysicFile.file_hash == file_hash))
        physic_file = req_physic.scalar_one_or_none()

        if not physic_file:
            s3_path = f"raw/{original_filename}"
            s3_client.upload_file(
                Filename=file_path,
                Bucket=settings.upload_bucket,
                Key=s3_path
            )

            metadata = extract_metadata_from_path(file_path, content_type, original_filename)

            physic_file = PhysicFile(
                file_hash=file_hash,
                s3_path=s3_path,
                file_size=file_size,
                mime_type=content_type,
                metadata_data=metadata
            )

            db.add(physic_file)
            await db.flush()
            print("Đã upload file mới")
        else:
            is_physic_exist = True
            print("File vật lý đã upload rồi")

        req_session = await db.execute(select(SessionFile).filter(SessionFile.chatbox_id == chatbox_id,
                                                    SessionFile.physic_file_id == physic_file.id))
        exist_session_file = req_session.scalar_one_or_none()
        
        if not exist_session_file:
            session_file = SessionFile(
                chatbox_id=chatbox_id,
                physic_file_id=physic_file.id,
                filename=unique_filename,
                status=FileStatus.PENDING.value
            )

            db.add(session_file)
            await db.flush()
            sessionfile_id = session_file.id
            print("Đã upload session file mới")
        else:
            sessionfile_id = exist_session_file.id
            print("Box này có file này rồi")

        return {"status": "Success", "file": original_filename, "is_physic_exist": is_physic_exist, "sessionfile_id": sessionfile_id}
    except Exception as e:
        print(e)
        if os.path.exists(file_path):
            os.remove(file_path)
    finally:
        print("Đã hoàn thành upload")