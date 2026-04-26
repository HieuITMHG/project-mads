from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

RO_DATABASE_URL = f"postgresql://{settings.readonly_user}:{settings.readonly_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"

ro_engine = create_engine(RO_DATABASE_URL, echo=False)

RO_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ro_engine)

def get_db_readonly():
    db = RO_SessionLocal()
    try:
        yield db
    finally:
        db.close()