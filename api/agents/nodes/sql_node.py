from typing import TypedDict, Sequence, Annotated
from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.graph import add_messages, StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from api.agents.olist_schema import OLIST_DB_SCHEMA
import os

from core.config import settings
import core.checkpointer as cp
from api.agents.nodes.supervisor_node import SupervisorState
from api.utils.logging_config import get_logger

logger = get_logger(__name__)

# --- 1. State ---
class SqlState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    instruction: str

# --- 2. Prompts & Tools ---
def get_sql_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/sql.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def get_sql_tools():
    # Chỉ lấy tool liên quan đến database (execute_sql) từ MCP
    return [t for t in cp.dynamic_mcp_tools if t.name == "execute_readonly_sql"]

# --- 3. Agent Logic ---
async def sql_agent(state: SqlState):
    """LLM Node for SQL Agent"""
    llm = ChatOpenAI(
        model="gpt-4o", # Sử dụng model tốt để viết SQL
        api_key=settings.openai_api_key,
        temperature=0
    )
    
    tools = get_sql_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    # Chuẩn bị system prompt kết hợp với instruction và schema
    sys_prompt = get_sql_prompt() + f"\n\n--- OLIST DATABASE SCHEMA ---\n{OLIST_DB_SCHEMA}"
    instruction = state.get("instruction", "")
    
    context_msg = f"Your specific task from the supervisor is:\n{instruction}"
    
    messages = [
        SystemMessage(content=sys_prompt),
        SystemMessage(content=context_msg)
    ] + list(state["messages"])
    
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

# Hàm kiểm tra xem LLM có gọi tool không, để định tuyến sang ToolNode
def should_continue(state: SqlState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if getattr(last_message, "tool_calls", None):
        tool_calls_count = sum(1 for m in messages if isinstance(m, AIMessage) and getattr(m, "tool_calls", None))
        if tool_calls_count >= 3:
            logger.warning("[SQL Agent] Vượt quá giới hạn 3 lần thử. Chuyển sang fallback.")
            return "fallback"
        return "tools"
    return END

def fallback_node(state: SqlState):
    """Node dự phòng khi vượt quá số lần thử tối đa."""
    return {"messages": [AIMessage(content="Tôi đã thử thực thi 3 lần nhưng vẫn gặp lỗi và không thể giải quyết được yêu cầu này. Vui lòng kiểm tra lại câu lệnh hoặc dữ liệu.")]}

# --- 4. Sub-Graph Compilation ---
builder = StateGraph(SqlState)
builder.add_node("sql_agent", sql_agent)

# Node thực thi tool - load tools at RUNTIME, not at import time
async def tool_executor_node(state: SqlState):
    """Runtime ToolNode: load tools dynamically khi graph thực sự chạy."""
    tools = get_sql_tools()
    if not tools:
        logger.error("[SQL Agent] Không tìm thấy SQL tools trong cp.dynamic_mcp_tools!")
        return {"messages": [ToolMessage(content="Lỗi hệ thống: SQL tool chưa được load. Vui lòng thử lại sau.", tool_call_id="error", name="execute_readonly_sql")]}
    node = ToolNode(tools)
    return await node.ainvoke(state)

builder.add_node("tools", tool_executor_node)

builder.add_node("fallback", fallback_node)

builder.add_edge(START, "sql_agent")
# Sau khi agent chạy, check điều kiện
builder.add_conditional_edges("sql_agent", should_continue)
# Sau khi tool chạy xong, quay lại agent để đánh giá kết quả
builder.add_edge("tools", "sql_agent")
builder.add_edge("fallback", END)

sql_graph = builder.compile()

# --- 5. Wrapper Node ---
async def SqlWrapper(state: SupervisorState, config: RunnableConfig):
    """Đóng gói sub-graph để dùng trong Main Graph"""
    instruction = state.get("current_instruction", "")
    logger.info("[SQL Wrapper] Nhận instruction: '%s'", instruction)
    
    sql_input = {
        "messages": [], # Khởi tạo luồng chat sạch cho SQL Agent
        "instruction": instruction
    }
    
    # Chạy sub-graph và truyền config xuống để UI streaming có thể catch được events
    result = await sql_graph.ainvoke(sql_input, config)
    
    # Lấy tin nhắn cuối cùng (chính là câu trả lời tổng hợp từ SQL Agent)
    last_msg = result["messages"][-1].content
    
    logger.info("[SQL Wrapper] Hoàn thành. Kết quả:\n%s...", last_msg[:200])
    
    # Lấy thông tin tool call từ tin nhắn cuối cùng của Supervisor để trả lời
    tool_call_id = state["messages"][-1].tool_calls[0]["id"] if state["messages"] and hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls else "unknown"
    tool_name = state["messages"][-1].tool_calls[0]["name"] if state["messages"] and hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls else "RouteToSQL"
    
    # Ném về Supervisor
    return {
        "messages": [ToolMessage(content="Thực thi hoàn tất. Kết quả đã được lưu vào collected_results.", tool_call_id=tool_call_id, name=tool_name)],
        "collected_results": [f"--- SQL Agent Output ---\nInstruction: {instruction}\nResult: {last_msg}\n------------------------"]
    }
