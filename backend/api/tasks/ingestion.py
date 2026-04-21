from core.worker import celery
from api.enums.file_type import FileType
from api.services.ingestion.upload import upload_to_s3
from core.postgres import SessionLocal

def parse_file():
    return "this is text after parse"

def chunk(text: str) -> list:
    return text.split(" ")

def embed(chunks: list) -> list:
    return [1,2,3,4,5,6,7]

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
        upload_to_s3(file_path=temp_path,
                    unique_filename=unique_filename,
                    original_filename=original_filename,
                    chatbox_id=chatbox_id,
                    content_type=content_type,
                    file_size=file_size,
                    db=db)
        db.commit()
        print("Đã upload xong!!!")
        
        if content_type == FileType.XLSX.value or FileType.CSV.value:
            return {"message": "Upload successfully!!"}
        else:
            parse_file()
            chunk()
            embed()
            return {"message": "Upload successfully!!"}
        
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close