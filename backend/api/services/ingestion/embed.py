from sqlalchemy.orm import Session
from core.qdrant import client
from core.embedder import embedder
from api.models.chunk  import DocumentChunk
from qdrant_client.models import PointStruct
from core.config import settings

def embed_chunks(db: Session, sessionfile_id: int, batch_size: int = 32):
    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.session_file_id == sessionfile_id,
        DocumentChunk.status == "PENDING"
    ).all()

    if not chunks:
        print("Không có chunk nào cần xử lý.")
        return
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.content for c in batch]
        embeddings = embedder.encode(texts)

        points = []

        for j, chunk in enumerate(batch):
            payload = {
                "session_file_id": sessionfile_id,
                "content": chunk.content,
                **chunk.headers 
            }

            points.append(PointStruct(
                id=chunk.id, 
                vector=embeddings[j].tolist(),
                payload=payload
            ))
        
        client.upsert(
            collection_name=settings.upload_collection,
            points=points
        )

        for chunk in batch:
            chunk.status = "COMPLETED"

        db.commit()
        print(f"Đã upload batch {i//batch_size + 1} thành công.")