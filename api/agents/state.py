from typing import TypedDict, Annotated, Sequence, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    chatbox_id: int
    selected_doc_ids: list[int]
    
    # State cho luồng SQL
    sql_query: str
    sql_result: list[dict]
    
    # State cho luồng Python (CSV/Excel)
    python_code: str
    python_output: str
    dataframe_paths: list[str] # Đường dẫn file CSV/Excel user đã up
    
    # Quản lý lỗi
    error_message: str
    retry_count: int