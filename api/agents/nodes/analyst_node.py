from typing import TypedDict, Sequence, Annotated
from langgraph.graph import add_messages, StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage, BaseMessage, SystemMessage
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
    return [t for t in cp.dynamic_mcp_tools if t.name == "run_python"]

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
        return "tools"
    return END

# --- 4. Sub-Graph Compilation ---
builder = StateGraph(AnalystState)
builder.add_node("analyst_agent", analyst_agent)

tools = get_analyst_tools()
tool_node = ToolNode(tools)
builder.add_node("tools", tool_node)

builder.add_edge(START, "analyst_agent")
builder.add_conditional_edges("analyst_agent", should_continue)
builder.add_edge("tools", "analyst_agent")

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
        "messages": [ToolMessage(content=f"Analyst Agent completed. Output:\n{last_msg}", tool_call_id=tool_call_id, name=tool_name)],
        "collected_results": [f"--- Analyst Agent Output ---\nInstruction: {instruction}\nResult: {last_msg}\n------------------------"]
    }