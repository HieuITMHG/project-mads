from typing import TypedDict, Sequence, Annotated
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage
from langgraph.graph import add_messages
import os
from langchain_openai import ChatOpenAI
from core.config import settings
from api.agents.nodes.supervisor_node import SupervisorState

def get_writer_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/writer.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

async def writer_node(state: SupervisorState):
    """
    Writer Node: Tổng hợp collected_results và messages để viết câu trả lời cuối cùng cho user.
    """
    messages = state.get("messages", [])
    collected_results = state.get("collected_results", [])
    
    # 1. Khởi tạo LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0.3 # Cho phép chút mượt mà trong văn phong
    )
    
    # 2. Xây dựng prompt
    system_prompt = get_writer_prompt()
    
    # Nếu không có kết quả nào, fallback
    if not collected_results:
        return {"messages": [AIMessage(content="I'm sorry, I couldn't find any relevant data or results to answer your question.")]}
        
    # Nối các kết quả lại
    results_str = "\n\n".join(collected_results)
    
    synthesis_instruction = (
        "Here are the Collected Results from the sub-agents:\n"
        f"--- COLLECTED RESULTS ---\n{results_str}\n-------------------------\n"
        "Please synthesize these results into a final response. Remember to preserve any <CHART_JSON> block exactly."
    )
    
    # 3. Gọi LLM. Chúng ta truyền system prompt, history, và context mới nhất.
    # Lấy câu hỏi gốc (HumanMessage) nếu có
    original_query = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            original_query = msg.content
            
    if original_query:
        synthesis_instruction = f"The user originally asked: '{original_query}'\n\n" + synthesis_instruction
        
    llm_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=synthesis_instruction)
    ]
    
    response = await llm.ainvoke(llm_messages)
    
    # 4. Trả về message cuối cùng. Ghi đè list collected_results thành rỗng (nếu muốn reset) hoặc giữ nguyên.
    # Ở đây theo design của add_messages, nó sẽ append AIMessage vào mảng messages.
    return {"messages": [response]}
