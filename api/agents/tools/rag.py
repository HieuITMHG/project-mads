from langchain.tools import InjectedState, tool
from typing_extensions import Annotated
from core.qdrant import client
from qdrant_client.models import Filter, FieldCondition, MatchAny
from core.config import settings
from core.embedder import embedder

@tool 
def search_rag(llm_rewrite_query: str, sessionfile_ids: Annotated[list, InjectedState("sessionfile_ids")]) -> list:
    "This is a tool receive rewrite query from LLM and retrieve context from qdrant"
    retrieved_contexts = client.query_points(
        collection_name=settings.upload_collection,
        query=embedder.encode(llm_rewrite_query),
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="session_file_id",
                    match=MatchAny(any=sessionfile_ids)
                )
            ]
        ),
        limit=10
    )

    contexts = []

    for point in retrieved_contexts.points: 
        payload = point.payload
        contexts.append(payload)

    return contexts