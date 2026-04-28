from sqlalchemy.ext.asyncio import AsyncSession
from api.models.message import Message

class ChatService:
    @staticmethod
    async def save_message(
        db: AsyncSession,
        chatbox_id: int,
        role: str,
        content: str,
        metadata_data: dict = None
    ) -> Message:
        new_msg = Message(
            chatbox_id=chatbox_id,
            role=role,
            content=content,
            metadata_data=metadata_data or {}
        )
        db.add(new_msg)
        await db.commit()
        await db.refresh(new_msg)
        return new_msg