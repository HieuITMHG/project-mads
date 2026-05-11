from sqlalchemy.ext.asyncio import AsyncSession
from api.models.message import Message

async def create_message(db: AsyncSession, chatbox_id, role, content: str):
    try:
        new_user_msg = Message(chatbox_id=chatbox_id, role="user", content=content)
        db.add(new_user_msg)
        await db.commit()
    except Exception as e:
        print(f"Lỗi khi tạo message mới: {e}")