from langchain_openai import ChatOpenAI
from core.config import settings

llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0
    )