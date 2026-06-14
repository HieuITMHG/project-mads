from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from api.utils.logging_config import get_logger
from core.config import settings
import operator

logger = get_logger(__name__)

def reset_or_add_results(left: list, right: list):
    """
    Reducer custom cho collected_results. 
    Nếu nhận được ["CLEAR"], nó sẽ reset danh sách về rỗng.
    Ngược lại, nó sẽ nối danh sách như operator.add.
    """
    if right and right[0] == "CLEAR":
        return []
    return operator.add(left, right)

async def manage_memory_node(state: dict, config: RunnableConfig):
    """
    Quản lý bộ nhớ: 
    1. Tóm tắt tin nhắn cũ để tránh tràn token.
    2. Reset collected_results từ lượt hỏi trước.
    """
    thread_id = config.get("configurable", {}).get("thread_id", "unknown")
    logger.info("[Thread:%s] Bắt đầu manage_memory_node", thread_id)
    
    updates = {}
    
    # 1. Reset collected_results nếu có (để bắt đầu lượt hỏi mới sạch sẽ)
    collected_results = state.get("collected_results", [])
    if collected_results:
        logger.debug("[Thread:%s] Resetting collected_results from previous turn.", thread_id)
        updates["collected_results"] = ["CLEAR"]
        
    delete_actions = []
    messages = state.get("messages", [])
    
    # Lọc bỏ các tin nhắn nội bộ (tool calls, tool results) của các lượt hỏi TRƯỚC.
    if messages:
        last_human_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                last_human_idx = i
                break
                
        if last_human_idx > 0:
            for i in range(last_human_idx):
                msg = messages[i]
                if isinstance(msg, ToolMessage) or (isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None)):
                    if msg.id:
                        delete_actions.append(RemoveMessage(id=msg.id))
                        
    # 2. Xử lý logic cắt giảm messages
    if len(messages) <= 10:
        if delete_actions:
            updates["messages"] = delete_actions
        return updates

    # Giữ lại tin nhắn đầu (0) và 6 tin nhắn cuối
    old_messages = messages[1:-6]
    
    if not old_messages:
        return updates

    logger.info("[Thread:%s] Memory Pruning triggered. Summarizing %d old messages.", thread_id, len(old_messages))

    current_summary = state.get("summary", "")
    
    old_chat_text = ""
    for m in old_messages:
        role = "User" if isinstance(m, HumanMessage) else "Assistant" if isinstance(m, AIMessage) else "Tool"
        content_preview = str(m.content)[:300] + "..." if len(str(m.content)) > 300 else str(m.content)
        old_chat_text += f"{role}: {content_preview}\n"

    summary_prompt = f"""Summarize the following part of the conversation. 
    Focus on what the user has asked so far, what actions the assistant has taken, and what the outcomes were.
    CRITICAL: You MUST preserve any important metadata, numerical figures, statistics, and specific data points (e.g., "56,164 reviews", "Top 1: Sao Paulo"). Do NOT generalize quantitative results, keep the exact numbers so they can be referenced later without recalculating.
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

    prune_delete_actions = [RemoveMessage(id=m.id) for m in old_messages if m.id]
    
    # Merge the two lists
    all_delete_actions = delete_actions + prune_delete_actions

    logger.info("[Thread:%s] Memory Pruning complete. Deleted %d messages. New summary created.", thread_id, len(all_delete_actions))
    
    updates["summary"] = new_summary
    updates["messages"] = all_delete_actions
    
    return updates
