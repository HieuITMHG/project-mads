from api.agents.tools.rag import search_rag
import core.checkpointer as cp
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage, RemoveMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from core.config import settings
from api.agents.olist_schema import OLIST_DB_SCHEMA
from api.utils.logging_config import get_logger
import time

logger = get_logger(__name__)

def get_tools():
    return [search_rag] + cp.dynamic_mcp_tools

BASE_SYSTEM_PROMPT = """You are MADS (Masterful Analytics & Data Science Assistant), an expert data analyst and database engineer. 
You are assisting a user in analyzing the Olist E-commerce dataset and other business documents.

You have access to the following tools:
1. 'search_rag': To retrieve context and information from user-uploaded text documents (PDFs, Docx).
2. 'execute_sql': To query the PostgreSQL database (strictly use SELECT statements).
3. 'run_python': To execute Python code in a secure sandbox for complex pandas data manipulation, statistical calculations, or generating charts.

CRITICAL INSTRUCTIONS:
1. DATA ACCURACY: NEVER hallucinate data, metrics, or column names. Always use the 'execute_sql' or 'run_python' tools to fetch real data before answering.
2. HANDLING ERRORS: If a tool returns an error, DO NOT panic. Read the error message, correct your code, and call the tool again.
3. VISUALIZATION (PLOTLY RULE): If the user asks for a chart/graph, you MUST strictly use the `plotly.express` or `plotly.graph_objects` library. Do NOT use `fig.show()`. Instead, extract the JSON representation using `fig.to_json()`, WRAP it in a `print()` call: `print(fig.to_json())`. In your final response, wrap the EXACT printed JSON string inside <CHART_JSON>...</CHART_JSON> tags.
   - ABSOLUTE RULE: You may ONLY include <CHART_JSON> in your response if the tool's Execution results literally contain the chart JSON string. If the tool returned a WARNING about empty output, you MUST fix your code and call the tool again — NEVER invent or fabricate chart JSON from memory.
4. PYTHON SANDBOX (UPLOADED FILES): When using 'run_python' to analyze uploaded files, DO NOT write code to read the files (e.g., `pd.read_csv()`). The library `pandas as pd` is already imported. The data is pre-loaded for you: if there is 1 uploaded file, use the global variable `df`. If there are multiple files, use the dictionary `dfs` (keys are file names).
5. CRITICAL: You are writing a standard Python script, NOT a Jupyter Notebook. You MUST explicitly use `print()` statements to output your final answers or data summaries. If you don't use `print()`, you will receive an empty output and MUST rewrite the code.
6. TABLE STRUCTURE: Pay attention to the relationships between tables in the Olist Database.

LANGUAGE RULE: 
You must perform all reasoning, coding, and database querying in English, formatted cleanly using Markdown.
"""

LOOP_BREAK_PROMPT = """
⚠️ LOOP DETECTION WARNING ⚠️
You have encountered {count} consecutive tool errors using the same approach.
MANDATORY ACTION: You MUST completely change your strategy now.

Options:
- Try a different tool or a simpler query
- Break the problem into smaller steps
- Admit to the user that you cannot complete this specific task and explain why
- Ask the user for clarification

DO NOT repeat the same failing code or query again.
"""

def _detect_consecutive_tool_errors(messages: list) -> tuple[int, str | None]:
    """
    Scan recent messages to detect consecutive ToolMessage errors.
    Returns (count, last_error_tool_name).
    """
    consecutive_errors = 0
    last_tool_name = None

    for msg in reversed(messages[-10:]):
        if not isinstance(msg, ToolMessage):
            break
        # ToolMessage.content có thể là string hoặc list (với MCP tools)
        raw_content = msg.content
        if isinstance(raw_content, list):
            content_lower = " ".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in raw_content
            ).lower()
        else:
            content_lower = (raw_content or "").lower()

        if any(kw in content_lower for kw in ("error", "exception", "traceback", "lỗi", "failed", "invalid")):
            consecutive_errors += 1
            if last_tool_name is None:
                last_tool_name = getattr(msg, "name", None)
        else:
            break

    return consecutive_errors, last_tool_name


async def manage_memory_node(state: dict, config: RunnableConfig):
    """
    Quản lý bộ nhớ: Tóm tắt các tin nhắn cũ và xóa chúng khỏi state để tránh tràn token.
    Giữ lại tin nhắn đầu tiên (chứa yêu cầu gốc) và 6 tin nhắn gần nhất.
    """
    messages = state.get("messages", [])
    if len(messages) <= 10:
        return {}

    # messages[0] thường là câu hỏi gốc của user. Giữ lại nó.
    # Giữ lại 6 tin nhắn cuối cùng để LLM có ngữ cảnh trực tiếp.
    old_messages = messages[1:-6]
    
    if not old_messages:
        return {}

    thread_id = config.get("configurable", {}).get("thread_id", "unknown")
    logger.info("[Thread:%s] Memory Pruning triggered. Summarizing %d old messages.", thread_id, len(old_messages))

    # Prepare summarization prompt
    current_summary = state.get("summary", "")
    
    # Rút trích text để gửi cho model tóm tắt
    old_chat_text = ""
    for m in old_messages:
        role = "User" if isinstance(m, HumanMessage) else "Assistant" if isinstance(m, AIMessage) else "Tool"
        content_preview = str(m.content)[:300] + "..." if len(str(m.content)) > 300 else str(m.content)
        old_chat_text += f"{role}: {content_preview}\n"

    summary_prompt = f"""Summarize the following part of the conversation. 
    Focus on what the user has asked so far, what actions the assistant has taken, and what the outcomes were.
    Do NOT include details of errors if they were already resolved.
    """
    if current_summary:
        summary_prompt += f"\n\nHere is the existing summary of earlier parts:\n{current_summary}"
        
    summary_prompt += f"\n\nNew messages to integrate into the summary:\n{old_chat_text}"

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0
    )
    
    summary_response = await llm.ainvoke([SystemMessage(content=summary_prompt)])
    new_summary = summary_response.content

    # Tạo lệnh xóa các tin nhắn cũ
    delete_actions = [RemoveMessage(id=m.id) for m in old_messages if m.id]

    logger.info("[Thread:%s] Memory Pruning complete. Deleted %d messages. New summary created.", thread_id, len(delete_actions))
    return {"summary": new_summary, "messages": delete_actions}


async def agent_reasoning_node(state: dict, config: RunnableConfig):
    thread_id = config.get("configurable", {}).get("thread_id", "unknown")
    t_start = time.perf_counter()
    logger.info("[Thread:%s] Agent reasoning node started. Messages in state: %d",
                thread_id, len(state.get("messages", [])))

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0
    )

    llm_with_tools = llm.bind_tools(get_tools())

    file_context = state.get("file_context", "")

    # 1. Static System Prompt (Hoàn toàn tĩnh -> Tỷ lệ Cache Hit cao nhất, tiết kiệm chi phí)
    static_system_prompt = f"""{BASE_SYSTEM_PROMPT}

    ---
    [OLIST DATABASE SCHEMA]
    {OLIST_DB_SCHEMA}
    """

    # 2. Dynamic Context Prompt (Chỉ thay đổi khi có file mới hoặc cập nhật summary)
    dynamic_context = f"""[USER UPLOADED FILES CONTEXT]
    {file_context if file_context else "No external files uploaded in this session."}"""

    summary = state.get("summary", "")
    if summary:
        dynamic_context += f"\n\n    ---\n    [SUMMARY OF EARLIER CONVERSATION]\n    {summary}"

    messages = [
        SystemMessage(content=static_system_prompt),
        SystemMessage(content=dynamic_context)
    ] + state["messages"]

    # --- Loop Detection ---
    error_count, error_tool = _detect_consecutive_tool_errors(state["messages"])
    if error_count >= 3:
        logger.warning(
            "[Thread:%s] Loop detected! %d consecutive tool errors (tool=%s). Injecting break prompt.",
            thread_id, error_count, error_tool
        )
        break_msg = SystemMessage(content=LOOP_BREAK_PROMPT.format(count=error_count))
        messages.insert(-1, break_msg)

    # --- Invoke LLM ---
    logger.debug("[Thread:%s] Invoking LLM with %d messages (including system)", thread_id, len(messages))
    response = await llm_with_tools.ainvoke(messages, config)

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    has_tool_calls = bool(getattr(response, "tool_calls", None))
    logger.info(
        "[Thread:%s] LLM responded in %.0fms | has_tool_calls=%s | tool_calls=%s",
        thread_id, elapsed_ms, has_tool_calls,
        [tc["name"] for tc in (response.tool_calls or [])]
    )

    return {"messages": [response]}