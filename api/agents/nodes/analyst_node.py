from typing import TypedDict, Sequence, Annotated
from langgraph.graph import add_messages, StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage, BaseMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
import os

from core.config import settings
import core.checkpointer as cp
from api.agents.nodes.supervisor_node import SupervisorState
from api.utils.logging_config import get_logger

logger = get_logger(__name__)

# --- 1. State ---
class AnalystState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    instruction: str
    file_context: str # Để LLM biết file nào đã được load vào sandbox

# --- 2. Prompts & Tools ---
def get_analyst_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/analyst.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def get_analyst_tools():
    # Chỉ lấy tool liên quan đến code/pandas (run_python) từ MCP
    return [t for t in cp.dynamic_mcp_tools if t.name == "run_data_analysis"]

# --- 3. Agent Logic ---
async def analyst_agent(state: AnalystState):
    """LLM Node for Analyst Agent"""
    llm = ChatOpenAI(
        model="gpt-4o", # Sử dụng model tốt để code python
        api_key=settings.openai_api_key,
        temperature=0
    )
    
    tools = get_analyst_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    # Chuẩn bị system prompt kết hợp với instruction và file_context
    sys_prompt = get_analyst_prompt()
    instruction = state.get("instruction", "")
    file_context = state.get("file_context", "No uploaded files.")
    
    context_msg = (
        f"Your specific task from the supervisor is:\n{instruction}\n\n"
        f"File Context (Already loaded in Sandbox):\n{file_context}"
    )
    
    messages = [
        SystemMessage(content=sys_prompt),
        SystemMessage(content=context_msg)
    ] + list(state["messages"])
    
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

# Hàm kiểm tra xem LLM có gọi tool không
def should_continue(state: AnalystState):
    messages = state["messages"]
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        tool_calls_count = sum(1 for m in messages if isinstance(m, AIMessage) and getattr(m, "tool_calls", None))
        if tool_calls_count >= 3:
            logger.warning("[Analyst Agent] Vượt quá giới hạn 3 lần thử. Chuyển sang fallback.")
            return "fallback"
        return "tools"
    return END

def fallback_node(state: AnalystState):
    """Node dự phòng khi vượt quá số lần thử tối đa."""
    return {"messages": [AIMessage(content="Tôi đã thử thực thi code Python 3 lần nhưng vẫn gặp lỗi và không thể giải quyết được yêu cầu này. Vui lòng cung cấp thêm thông tin hoặc kiểm tra lại yêu cầu.")]}

# --- 4. Sub-Graph Compilation ---
builder = StateGraph(AnalystState)
builder.add_node("analyst_agent", analyst_agent)

# Node thực thi tool - load tools at RUNTIME, not at import time
async def tool_executor_node(state: AnalystState):
    """Runtime ToolNode: load tools dynamically khi graph thực sự chạy."""
    tools = get_analyst_tools()
    if not tools:
        logger.error("[Analyst Agent] Không tìm thấy Analyst tools trong cp.dynamic_mcp_tools!")
        return {"messages": [ToolMessage(content="Lỗi hệ thống: Analyst tool chưa được load. Vui lòng thử lại sau.", tool_call_id="error", name="run_data_analysis")]}
    node = ToolNode(tools)
    return await node.ainvoke(state)

builder.add_node("tools", tool_executor_node)

builder.add_node("fallback", fallback_node)

builder.add_edge(START, "analyst_agent")
builder.add_conditional_edges("analyst_agent", should_continue)
builder.add_edge("tools", "analyst_agent")
builder.add_edge("fallback", END)

analyst_graph = builder.compile()

# --- 5. Wrapper Node ---
async def AnalystWrapper(state: SupervisorState, config: RunnableConfig):
    """Đóng gói sub-graph để dùng trong Main Graph"""
    instruction = state.get("current_instruction", "")
    file_context = state.get("file_context", "")
    logger.info("[Analyst Wrapper] Nhận instruction: '%s'", instruction)
    
    analyst_input = {
        "messages": [], # Khởi tạo luồng chat sạch cho Analyst Agent
        "instruction": instruction,
        "file_context": file_context
    }
    
    # Chạy sub-graph và truyền config xuống để UI streaming có thể catch được events
    result = await analyst_graph.ainvoke(analyst_input, config)
    
    # Lấy tin nhắn cuối cùng (chính là câu trả lời tổng hợp từ Analyst Agent)
    last_msg = result["messages"][-1].content
    
    logger.info("[Analyst Wrapper] Hoàn thành. Kết quả:\n%s...", last_msg[:200])
    
    # Lấy thông tin tool call từ tin nhắn cuối cùng của Supervisor để trả lời
    tool_call_id = state["messages"][-1].tool_calls[0]["id"] if state["messages"] and hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls else "unknown"
    tool_name = state["messages"][-1].tool_calls[0]["name"] if state["messages"] and hasattr(state["messages"][-1], "tool_calls") and state["messages"][-1].tool_calls else "RouteToAnalyst"
    
    # Ném về Supervisor
    return {
        "messages": [ToolMessage(content="Thực thi hoàn tất. Kết quả đã được lưu vào collected_results.", tool_call_id=tool_call_id, name=tool_name)],
        "collected_results": [f"--- Analyst Agent Output ---\nInstruction: {instruction}\nResult: {last_msg}\n------------------------"]
    }