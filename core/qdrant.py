from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from core.config import settings

client = QdrantClient(url=settings.qdrant_endpoint, api_key=settings.qdrant_key)

test_client = QdrantClient(url="http://localhost:6333/", api_key=settings.qdrant_key)

# if not client.collection_exists(settings.upload_collection):
#     client.create_collection(
#         collection_name=settings.upload_collection,
#         vectors_config=VectorParams(size=384, distance=Distance.COSINE),
#     )