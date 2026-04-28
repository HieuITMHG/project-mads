from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.config import settings

RO_DATABASE_URL = f"postgresql+asyncpg://{settings.readonly_user}:{settings.readonly_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

ro_engine = create_async_engine(RO_DATABASE_URL, echo=False)

RO_SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=ro_engine, class_=AsyncSession)

async def get_db_readonly():
    async with RO_SessionLocal() as db:
        yield db