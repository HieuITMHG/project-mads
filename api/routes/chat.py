from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from sqlalchemy.future import select
from typing import List
import json
from datetime import datetime, timezone, timedelta
import httpx

from core.postgres import get_db
from api.models.chat_box import ChatBox
from api.models.message import Message
from api.models.session_file import SessionFile
from api.models.physic_file import PhysicFile
from langchain_core.messages import ToolMessage

from api.deps import get_current_active_user
from api.schemas.chat import ChatBoxResponse, MessageResponse, ApprovalRequest, ChatHistoryResponse
from api.utils.chart_parser import extract_chart_metadata
from api.repositories import message_repo, file_repo

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

    config = {"configurable": {"thread_id": str(chatbox_id)}}
    current_state = await cp.agent_app.aget_state(config)
    pending_tools = None
    if current_state and current_state.next and "tools" in current_state.next:
        try:
            pending_tools = current_state.values["messages"][-1].tool_calls
        except (KeyError, IndexError, AttributeError):
            pass

    return {
        "chatbox_id": chat.id,
        "title": chat.title,
        "messages": msgs_req.scalars().all(),
        "session_files": files_req.scalars().all(),
        "pending_tools": pending_tools
    }

async def create_context(sessionfile_ids: list[int], db: AsyncSession, chatbox_id: int):
    file_context_str = ""

    if sessionfile_ids:
        files_req = await file_repo.get_box_files(db=db, sessionfile_ids=sessionfile_ids, chatbox_id=chatbox_id)

        session_files_data = files_req.all()
        s3_paths_to_prepare = []
        files_to_update = []
        now = datetime.now(timezone.utc)

        for session_file, physic_file in session_files_data:
            if session_file.sandbox_expires_at is None or \
               (session_file.sandbox_expires_at - now).total_seconds() < 300:
                s3_paths_to_prepare.append(physic_file.s3_path)
                files_to_update.append(session_file)

        if s3_paths_to_prepare:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        "http://sandbox_api:8002/prepare_file_data", 
                        json={
                            "session_id": str(chatbox_id), 
                            "s3_path_lst": s3_paths_to_prepare
                        },
                        timeout=60.0 
                    )
                    response.raise_for_status()
                    
                    new_expiry = now + timedelta(hours=1)
                    for sf in files_to_update:
                        sf.sandbox_expires_at = new_expiry
                    await db.commit()
                except Exception as e:
                    print(f"Error calling Sandbox API to prepare files: {e}")
                    raise HTTPException(status_code=500, detail="Unable to prepare data files")
                
        file_context_str += "Information about the attached files in this session:\n"
        file_context_str += f"""
        --- IMPORTANT:
        Your current environment has the session_id: {chatbox_id}.
        Whenever you run the 'run_data_analysis' tool (or your Python execution tool), you MUST pass the parameter session_id="{chatbox_id}".
        ---
        """
        
        for session_file, physic_file in session_files_data:
            mime = physic_file.mime_type.lower()
            
            if "spreadsheet" in mime or "excel" in mime or "csv" in mime:
                schema_json = physic_file.metadata_data if physic_file.metadata_data else "No explicit schema available"
                
                sandbox_absolute_path = f"/workspace/{chatbox_id}/{session_file.display_filename}"
                
                file_context_str += f"""
                - [DATA FILE]: {session_file.display_filename}
                - Category: Tabular Data.
                - MANDATORY FILE PATH FOR CODE: `{sandbox_absolute_path}`
                - Example usage: `pd.read_csv('{sandbox_absolute_path}')` (adjust the read function based on the file extension).
                - Schema / Structure: {schema_json}
                -------------------
                """

        return file_context_str

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

    config = {"configurable": {"thread_id": str(chatbox_id)}}
    current_state = await cp.agent_app.aget_state(config)
    if current_state and current_state.next and "tools" in current_state.next:
        raise HTTPException(status_code=400, detail="Bạn đang có yêu cầu phê duyệt công cụ (Human-in-the-loop) chưa hoàn thành. Hãy tải lại trang và phê duyệt/từ chối trước khi tiếp tục.")

    await message_repo.create_message(db=db, chatbox_id=chatbox_id, role="user", content=prompt)

    file_context_str = await create_context(sessionfile_ids=sessionfile_ids, chatbox_id=chatbox_id, db=db)

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
            yield f"data: {json.dumps({'type': 'status', 'content': 'Agent đang suy nghĩ...'})}\n\n"
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
            yield f"data: {json.dumps({'type': 'status', 'content': 'Đang tiếp tục suy nghĩ...'})}\n\n"
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