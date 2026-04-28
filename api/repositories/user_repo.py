from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from api.models.user import User

async def get_user(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalar_one_or_none()
    return user
