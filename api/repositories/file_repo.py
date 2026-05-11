from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.models.session_file import SessionFile
from api.models.physic_file import PhysicFile

async def get_box_files(db: AsyncSession, chatbox_id: int, sessionfile_ids: list[int]):
    try:
        files_req = await db.execute(
            select(SessionFile, PhysicFile)
            .join(PhysicFile, SessionFile.physic_file_id == PhysicFile.id)
            .filter(SessionFile.id.in_(sessionfile_ids), SessionFile.chatbox_id == chatbox_id)
        )

        return files_req
    except Exception as e:
        print(f"Lỗi khi try vấn chatbox file {e}")
        raise