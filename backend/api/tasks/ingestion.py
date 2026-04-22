from core.worker import celery
from api.enums.file_type import FileType
from api.services.ingestion.upload import upload_to_s3
from api.services.ingestion.parse import parse_file
from api.services.ingestion.chunk import split_markdown
from api.services.ingestion.embed import embed_chunks
from core.postgres import SessionLocal


@celery.task(name="ingest_upload_file")
def ingest_upload_file(temp_path: str, 
                        unique_filename: str, 
                        content_type: str,
                        original_filename: str, 
                        chatbox_id: int, 
                        user_id: int,
                        file_size: int):
    
    db = SessionLocal()

    try:

        print("Đang upload và tạo session file!!!")
        result = upload_to_s3(file_path=temp_path,
                    unique_filename=unique_filename,
                    original_filename=original_filename,
                    chatbox_id=chatbox_id,
                    content_type=content_type,
                    file_size=file_size,
                    db=db)
        print("Đã upload xong!!!")
        
        if content_type == FileType.XLSX.value or content_type==FileType.CSV.value:
            db.commit()
            return {"message": "Upload successfully!!"}

        if not result["is_physic_exist"]:
            markdown = parse_file(file_path=temp_path)
            split_markdown(md_doc=markdown, db=db, sessionfile_id=result["sessionfile_id"])
            embed_chunks(db=db, sessionfile_id=result["sessionfile_id"])

        db.commit()
        return {"message": "Upload successfully!!"}
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close