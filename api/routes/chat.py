from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from sqlalchemy.future import select
from typing import List
import json

from core.postgres import get_db
from api.models.chat_box import ChatBox
from api.models.message import Message
from api.models.session_file import SessionFile
from api.models.physic_file import PhysicFile
from langchain_core.messages import ToolMessage

from api.deps import get_current_active_user
from api.schemas.chat import ChatBoxResponse, MessageResponse, ApprovalRequest, ChatHistoryResponse
from api.utils.chart_parser import extract_chart_metadata

import core.checkpointer as cp

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=ChatBoxResponse)
async def create_new_chat(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    new_chat = ChatBox(user_id=current_user.id, title="Cuộc trò chuyện mới")
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return new_chat

@router.get("/", response_model=List[ChatBoxResponse])
async def get_user_chats(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    result = await db.execute(select(ChatBox).filter(ChatBox.user_id == current_user.id).order_by(ChatBox.created_at.desc()))
    return result.scalars().all()

@router.get("/{chatbox_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    chatbox_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user = Depends(get_current_active_user)
):
    chat_req = await db.execute(
        select(ChatBox).filter(ChatBox.id == chatbox_id, ChatBox.user_id == current_user.id)
    )
    chat = chat_req.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện hoặc bạn không có quyền")
    
    msgs_req = await db.execute(
        select(Message).filter(Message.chatbox_id == chatbox_id).order_by(Message.created_at.asc())
    )

    files_req = await db.execute(
        select(SessionFile).filter(SessionFile.chatbox_id == chatbox_id).order_by(SessionFile.created_at.desc())
    )

    return {
        "chatbox_id": chat.id,
        "title": chat.title,
        "messages": msgs_req.scalars().all(),
        "session_files": files_req.scalars().all()
    }

@router.post("/{chatbox_id}/stream")
async def chat_stream(
    chatbox_id: int, 
    prompt: str, 
    sessionfile_ids: list[int],
    db: AsyncSession = Depends(get_db), 
    current_user = Depends(get_current_active_user)
):
    chat_req = await db.execute(select(ChatBox).filter(ChatBox.id == chatbox_id, ChatBox.user_id == current_user.id))
    if not chat_req.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")

    new_user_msg = Message(chatbox_id=chatbox_id, role="user", content=prompt)
    db.add(new_user_msg)
    await db.commit()

    file_context_str = ""
    if sessionfile_ids:
        file_context_str += "THÔNG TIN CÁC FILE ĐÍNH KÈM TRONG PHIÊN NÀY:\n"
        files_req = await db.execute(
            select(SessionFile, PhysicFile)
            .join(PhysicFile, SessionFile.physic_file_id == PhysicFile.id)
            .filter(SessionFile.id.in_(sessionfile_ids), SessionFile.chatbox_id == chatbox_id)
        )
        
        for session_file, physic_file in files_req.all():
            mime = physic_file.mime_type.lower()
            
            if "spreadsheet" in mime or "excel" in mime or "csv" in mime:
                schema_json = physic_file.metadata_data if physic_file.metadata_data else "Không có cấu trúc rõ ràng"
                file_context_str += f"""
                - 📊 [DATA FILE]: {session_file.filename}
                - Phân loại: Dữ liệu dạng bảng (Sử dụng công cụ 'run_python' với pandas để phân tích).
                - Đường dẫn vật lý: {physic_file.s3_path}
                - Cấu trúc: {schema_json}
                -------------------
                """
            
            else:
                file_context_str += f"""
                - 📄 [DOCUMENT FILE]: {session_file.filename}
                - ID Tài liệu: {session_file.id}
                - Phân loại: Văn bản phi cấu trúc.
                - Hướng dẫn: Không có schema. Để đọc nội dung file này, HÃY SỬ DỤNG CÔNG CỤ 'search_rag' và truyền ID Tài liệu ({session_file.id}) cùng với từ khóa tìm kiếm.
                -------------------
                """

    config = {"configurable": {"thread_id": str(chatbox_id)}}
    input_state = {
        "messages": [("user", prompt)],
        "sessionfile_ids": sessionfile_ids,
        "file_context": file_context_str  
    }

    async def event_generator():
        full_ai_response = ""
        hitl_triggered = False

        try:
            async for event in cp.agent_app.astream_events(input_state, config=config, version="v2"):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        full_ai_response += content
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    yield f"data: {json.dumps({'type': 'status', 'content': f'Đang chạy công cụ: {tool_name}...'})}\n\n"

            current_state = await cp.agent_app.aget_state(config)
            if current_state.next and "tools" in current_state.next:
                hitl_triggered = True
                pending_tools = current_state.values["messages"][-1].tool_calls
                yield f"data: {json.dumps({'type': 'hitl_approval_required', 'tool_calls': pending_tools})}\n\n"

            yield "data: [DONE]\n\n"
            
            if not hitl_triggered and full_ai_response.strip():
                clean_content, chart_meta = extract_chart_metadata(full_ai_response)
                new_ai_msg = Message(
                    chatbox_id=chatbox_id, 
                    role="assistant", 
                    content=clean_content,
                    metadata_data=chart_meta
                )
                db.add(new_ai_msg)
                await db.commit()

        except Exception as e:
            print(f"Lỗi Stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{chatbox_id}/approve")
async def approve_tool_call(
    chatbox_id: int, 
    req: ApprovalRequest,
    db: AsyncSession = Depends(get_db), 
    current_user = Depends(get_current_active_user)
):
    chat_req = await db.execute(select(ChatBox).filter(ChatBox.id == chatbox_id, ChatBox.user_id == current_user.id))
    if not chat_req.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")

    config = {"configurable": {"thread_id": str(chatbox_id)}}
    current_state = await cp.agent_app.aget_state(config)
    
    if req.action == "edit":
        last_message = current_state.values["messages"][-1]
        last_message.tool_calls[0]["args"] = req.edited_args
        await cp.agent_app.aupdate_state(config, {"messages": [last_message]})
        
    elif req.action == "reject":
        last_message = current_state.values["messages"][-1]
        tool_call_id = last_message.tool_calls[0]["id"]
        tool_name = last_message.tool_calls[0]["name"]
        
        reject_message = ToolMessage(
            tool_call_id=tool_call_id,
            name=tool_name,
            content="LỖI: Người dùng đã từ chối thực thi lệnh này. Hãy xin lỗi hoặc đề xuất phương án phân tích khác."
        )
        await cp.agent_app.aupdate_state(config, {"messages": [reject_message]}, as_node="tools")

    async def resume_event_generator():
        full_ai_response = ""
        hitl_triggered = False 

        try:
            async for event in cp.agent_app.astream_events(None, config=config, version="v2"):
                kind = event["event"]
                
                if kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'status', 'content': 'Đang thực thi công cụ...'})}\n\n"
                    
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        full_ai_response += content
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            
            current_state = await cp.agent_app.aget_state(config)
            if current_state.next and "tools" in current_state.next:
                hitl_triggered = True
                pending_tools = current_state.values["messages"][-1].tool_calls
                yield f"data: {json.dumps({'type': 'hitl_approval_required', 'tool_calls': pending_tools})}\n\n"

            yield "data: [DONE]\n\n"
            
            if not hitl_triggered and full_ai_response.strip():
                clean_content, chart_meta = extract_chart_metadata(full_ai_response)
                new_ai_msg = Message(
                    chatbox_id=chatbox_id, 
                    role="assistant", 
                    content=clean_content,
                    metadata_data=chart_meta
                )
                db.add(new_ai_msg)
                await db.commit()
                
        except Exception as e:
            print(f"Lỗi Resume Stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(resume_event_generator(), media_type="text/event-stream")