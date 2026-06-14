import operator
import os
from typing import TypedDict, Sequence, Annotated, List
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import add_messages
from langgraph.types import Command
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from core.config import settings
from api.agents.tools.rag import search_rag
from api.utils.logging_config import get_logger
from api.agents.nodes.memory_node import reset_or_add_results

logger = get_logger(__name__)

class SupervisorState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    collected_results: Annotated[List[str], reset_or_add_results]
    current_instruction: str
    chatbox_id: int
    sessionfile_ids: list[int]
    file_context: str
    summary: str

# Định nghĩa các công cụ điều hướng để LLM gọi
class RouteToSQL(BaseModel):
    """Delegate task to the SQL Agent to query the database."""
    instruction: str = Field(description="Clear instruction for the SQL agent to extract data.")

class RouteToAnalyst(BaseModel):
    """Delegate task to the Analyst Agent for pandas manipulation or Plotly chart generation."""
    instruction: str = Field(description="Clear instruction for the Analyst agent, indicating what to calculate or plot.")

class RouteToWriter(BaseModel):
    """Send collected results to the Writer agent to formulate the final answer."""
    pass

def get_supervisor_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/supervisor.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

async def Supervisor(state: SupervisorState):
    logger.info("--- [Supervisor Node] Đang kiểm tra state... ---")
    
    llm = ChatOpenAI(
        model="gpt-4o", # Supervisor cần model thông minh để quyết định
        api_key=settings.openai_api_key,
        temperature=0
    )
    
    # Ràng buộc LLM với RAG tool và các Routing schema, tắt gọi tool song song
    tools = [search_rag, RouteToSQL, RouteToAnalyst, RouteToWriter]
    llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)
    
    sys_prompt = get_supervisor_prompt()
    results_str = "\n\n".join(state.get("collected_results", []))
    summary_str = state.get("summary", "")
    
    context_msg = f"Collected Results so far:\n{results_str if results_str else 'None'}"
    if summary_str:
        context_msg += f"\n\n--- PREVIOUS CONVERSATION SUMMARY ---\n{summary_str}\n(Note: Use this summary only if the user refers to past context)"
    
    # Vòng lặp nội bộ để xử lý công cụ RAG trực tiếp trong Supervisor mà không cần rời khỏi node
    messages = [
        SystemMessage(content=sys_prompt),
        SystemMessage(content=context_msg)
    ] + list(state["messages"])
    
    new_messages_to_state = []
    
    while True:
        response = await llm_with_tools.ainvoke(messages)
        
        # Nếu LLM không gọi tool nào, nghĩa là nó muốn trả lời trực tiếp (ví dụ: chào hỏi)
        if not response.tool_calls:
            logger.info("-> [Supervisor] Trả lời trực tiếp người dùng.")
            new_messages_to_state.append(response)
            return Command(
                update={"messages": new_messages_to_state},
                goto="__end__"
            )
            
        # Kiểm tra xem tool nào được gọi
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name == "RouteToSQL":
            logger.info("-> [Supervisor] Điều phối sang SQL Agent: %s", tool_args['instruction'])
            new_messages_to_state.append(response)
            return Command(
                update={
                    "current_instruction": tool_args["instruction"],
                    "messages": new_messages_to_state
                },
                goto="sql_wrapper"
            )
            
        elif tool_name == "RouteToAnalyst":
            logger.info("-> [Supervisor] Điều phối sang Analyst Agent: %s", tool_args['instruction'])
            new_messages_to_state.append(response)
            return Command(
                update={
                    "current_instruction": tool_args["instruction"],
                    "messages": new_messages_to_state
                },
                goto="analyst_wrapper"
            )
            
        elif tool_name == "RouteToWriter":
            logger.info("-> [Supervisor] Điều phối sang Writer để tổng hợp kết quả.")
            new_messages_to_state.append(response)
            return Command(
                update={"messages": new_messages_to_state},
                goto="writer_node"
            )
            
        elif tool_name == "search_rag":
            # Chạy RAG cục bộ và tiếp tục vòng lặp LLM
            logger.info("-> [Supervisor] Đang tìm kiếm RAG: %s", tool_args)
            
            # Vì gọi thủ công qua .invoke() thay vì dùng ToolNode của LangGraph, ta phải tự inject state vào
            current_session_ids = state.get("sessionfile_ids", [])
            logger.info("-> [Supervisor] RAG session_ids từ State: %s", current_session_ids)
            invoke_args = {**tool_args, "sessionfile_ids": current_session_ids}
            rag_result = search_rag.invoke(invoke_args)

            logger.info("RAG result: %s", str(rag_result))
            
            tool_msg = ToolMessage(content=str(rag_result), tool_call_id=tool_call["id"], name=tool_name)
            
            # Thêm AI message gọi tool và Tool message kết quả vào history của vòng lặp này
            messages.append(response)
            messages.append(tool_msg)
            
            # Đồng thời chuẩn bị append vào State
            new_messages_to_state.append(response)
            new_messages_to_state.append(tool_msg)
            
            logger.info("-> [Supervisor] Đã có kết quả RAG, LLM đang phân tích tiếp...")
            continue
            
        else:
            # Fallback
            return Command(goto="__end__")