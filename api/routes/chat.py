from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from sqlalchemy.future import select
from typing import List
import json
from datetime import datetime, timezone, timedelta
import httpx
import time

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
from api.utils.logging_config import get_logger

import core.checkpointer as cp

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatBoxResponse)
async def create_new_chat(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_active_user)):
    new_chat = ChatBox(user_id=current_user.id, title="Cuộc trò chuyện mới")
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    logger.info("New chat created: id=%d user=%d", new_chat.id, current_user.id)
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
            logger.info("[Chat:%d] Preparing %d file(s) in sandbox...", chatbox_id, len(s3_paths_to_prepare))
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
                    logger.info("[Chat:%d] Sandbox file preparation succeeded.", chatbox_id)
                except Exception as e:
                    logger.error("[Chat:%d] Sandbox API prepare_file_data failed: %s", chatbox_id, e, exc_info=True)
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


def _now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, max_len: int = 500) -> str:
    """Truncate long strings for safe SSE transport."""
    if not text:
        return ""
    text = str(text)
    return text[:max_len] + "…" if len(text) > max_len else text


def _extract_tool_output_text(tool_output) -> str:
    """
    Extract plain text from a tool output.
    MCP tools return content as a list of dicts: [{'type': 'text', 'text': '...'}]
    Regular tools return a plain string or other type.
    """
    if isinstance(tool_output, list):
        parts = []
        for item in tool_output:
            if isinstance(item, dict):
                parts.append(item.get("text", str(item)))
            else:
                parts.append(str(item))
        return " ".join(parts)
    # Handle LangChain ToolMessage objects
    if hasattr(tool_output, "content"):
        return _extract_tool_output_text(tool_output.content)
    return str(tool_output) if tool_output is not None else ""


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

    logger.info("[Chat:%d] Stream started. User=%d | prompt_preview=%s",
                chatbox_id, current_user.id, _truncate(prompt, 100))

    async def event_generator():
        full_ai_response = ""
        hitl_triggered = False
        # Track active tool timers: tool_call_id -> start_time
        tool_timers: dict[str, float] = {}

        try:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Agent đang suy nghĩ...', 'timestamp': _now_iso()})}\n\n"

            async for event in cp.agent_app.astream_events(input_state, config=config, version="v2"):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        full_ai_response += content
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "unknown_tool")
                    run_id = event.get("run_id", tool_name)
                    tool_input = event.get("data", {}).get("input", {})
                    tool_timers[run_id] = time.perf_counter()

                    logger.info("[Chat:%d] Tool START → %s | args=%s", chatbox_id, tool_name, _truncate(str(tool_input), 200))

                    yield f"data: {json.dumps({
                        'type': 'tool_start',
                        'run_id': run_id,
                        'tool_name': tool_name,
                        'args': tool_input,
                        'timestamp': _now_iso()
                    })}\n\n"

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown_tool")
                    run_id = event.get("run_id", tool_name)
                    tool_output = event.get("data", {}).get("output", "")
                    
                    duration_ms = 0
                    if run_id in tool_timers:
                        duration_ms = int((time.perf_counter() - tool_timers.pop(run_id)) * 1000)

                    output_preview = _truncate(_extract_tool_output_text(tool_output), 400)
                    is_error = any(kw in output_preview.lower() for kw in ("error", "exception", "traceback", "failed"))

                    logger.info("[Chat:%d] Tool END ← %s | duration=%dms | is_error=%s | preview=%s",
                                chatbox_id, tool_name, duration_ms, is_error, _truncate(output_preview, 100))

                    yield f"data: {json.dumps({
                        'type': 'tool_end',
                        'run_id': run_id,
                        'tool_name': tool_name,
                        'output_preview': output_preview,
                        'duration_ms': duration_ms,
                        'is_error': is_error,
                        'timestamp': _now_iso()
                    })}\n\n"

            current_state = await cp.agent_app.aget_state(config)
            if current_state.next and "tools" in current_state.next:
                hitl_triggered = True
                pending_tools = current_state.values["messages"][-1].tool_calls
                logger.info("[Chat:%d] HITL triggered. Waiting for user approval on tools: %s",
                            chatbox_id, [tc["name"] for tc in pending_tools])
                yield f"data: {json.dumps({'type': 'hitl_approval_required', 'tool_calls': pending_tools, 'timestamp': _now_iso()})}\n\n"

            yield "data: [DONE]\n\n"
            logger.info("[Chat:%d] Stream completed. hitl=%s | response_len=%d",
                        chatbox_id, hitl_triggered, len(full_ai_response))
            
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
            logger.error("[Chat:%d] Stream error: %s", chatbox_id, e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'timestamp': _now_iso()})}\n\n"

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

    logger.info("[Chat:%d] HITL action=%s from user=%d", chatbox_id, req.action, current_user.id)
    
    if req.action == "edit":
        last_message = current_state.values["messages"][-1]
        last_message.tool_calls[0]["args"] = req.edited_args
        await cp.agent_app.aupdate_state(config, {"messages": [last_message]})
        logger.info("[Chat:%d] Tool args edited: %s", chatbox_id, _truncate(str(req.edited_args), 200))
        
    elif req.action == "reject":
        last_message = current_state.values["messages"][-1]
        tool_call_id = last_message.tool_calls[0]["id"]
        tool_name = last_message.tool_calls[0]["name"]
        logger.info("[Chat:%d] Tool rejected: %s (id=%s)", chatbox_id, tool_name, tool_call_id)
        
        reject_message = ToolMessage(
            tool_call_id=tool_call_id,
            name=tool_name,
            content="LỖI: Người dùng đã từ chối thực thi lệnh này. Hãy xin lỗi hoặc đề xuất phương án phân tích khác."
        )
        await cp.agent_app.aupdate_state(config, {"messages": [reject_message]}, as_node="tools")

    async def resume_event_generator():
        full_ai_response = ""
        hitl_triggered = False
        tool_timers: dict[str, float] = {}

        try:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Đang tiếp tục suy nghĩ...', 'timestamp': _now_iso()})}\n\n"

            async for event in cp.agent_app.astream_events(None, config=config, version="v2"):
                kind = event["event"]
                
                if kind == "on_tool_start":
                    tool_name = event.get("name", "unknown_tool")
                    run_id = event.get("run_id", tool_name)
                    tool_input = event.get("data", {}).get("input", {})
                    tool_timers[run_id] = time.perf_counter()

                    logger.info("[Chat:%d] Tool START (resume) → %s | args=%s",
                                chatbox_id, tool_name, _truncate(str(tool_input), 200))

                    yield f"data: {json.dumps({
                        'type': 'tool_start',
                        'run_id': run_id,
                        'tool_name': tool_name,
                        'args': tool_input,
                        'timestamp': _now_iso()
                    })}\n\n"

                elif kind == "on_tool_end":
                    tool_name = event.get("name", "unknown_tool")
                    run_id = event.get("run_id", tool_name)
                    tool_output = event.get("data", {}).get("output", "")

                    duration_ms = 0
                    if run_id in tool_timers:
                        duration_ms = int((time.perf_counter() - tool_timers.pop(run_id)) * 1000)

                    output_preview = _truncate(_extract_tool_output_text(tool_output), 400)
                    is_error = any(kw in output_preview.lower() for kw in ("error", "exception", "traceback", "failed"))

                    logger.info("[Chat:%d] Tool END (resume) ← %s | duration=%dms | is_error=%s",
                                chatbox_id, tool_name, duration_ms, is_error)

                    yield f"data: {json.dumps({
                        'type': 'tool_end',
                        'run_id': run_id,
                        'tool_name': tool_name,
                        'output_preview': output_preview,
                        'duration_ms': duration_ms,
                        'is_error': is_error,
                        'timestamp': _now_iso()
                    })}\n\n"
                    
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        full_ai_response += content
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            
            current_state = await cp.agent_app.aget_state(config)
            if current_state.next and "tools" in current_state.next:
                hitl_triggered = True
                pending_tools = current_state.values["messages"][-1].tool_calls
                logger.info("[Chat:%d] HITL triggered again after resume. tools=%s",
                            chatbox_id, [tc["name"] for tc in pending_tools])
                yield f"data: {json.dumps({'type': 'hitl_approval_required', 'tool_calls': pending_tools, 'timestamp': _now_iso()})}\n\n"

            yield "data: [DONE]\n\n"
            logger.info("[Chat:%d] Resume stream completed. hitl=%s | response_len=%d",
                        chatbox_id, hitl_triggered, len(full_ai_response))
            
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
            logger.error("[Chat:%d] Resume stream error: %s", chatbox_id, e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'timestamp': _now_iso()})}\n\n"

    return StreamingResponse(resume_event_generator(), media_type="text/event-stream")