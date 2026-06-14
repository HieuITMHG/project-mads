from langgraph.graph import StateGraph, START, END

# Import các node và state
from api.agents.nodes.supervisor_node import SupervisorState, Supervisor
from api.agents.nodes.sql_node import SqlWrapper
from api.agents.nodes.analyst_node import AnalystWrapper
from api.agents.nodes.writer_node import writer_node
from api.agents.nodes.memory_node import manage_memory_node

def build_agent_graph():
    """
    Build the main hierarchical agent graph with Supervisor as the router.
    """
    workflow = StateGraph(SupervisorState)
    
    # 1. Thêm các Node
    # Thêm memory node vào đầu luồng để đảm bảo không bị tràn token
    workflow.add_node("manage_memory", manage_memory_node)
    
    workflow.add_node("supervisor", Supervisor)
    workflow.add_node("sql_wrapper", SqlWrapper)
    workflow.add_node("analyst_wrapper", AnalystWrapper)
    workflow.add_node("writer_node", writer_node)
    
    # 2. Định nghĩa các luồng (Edges)
    # Bắt đầu -> Manage Memory -> Supervisor
    workflow.add_edge(START, "manage_memory")
    workflow.add_edge("manage_memory", "supervisor")
    
    # Các luồng từ Supervisor đi ra được quyết định tự động bởi object Command 
    # (trong code supervisor_node.py đã trả về Command(goto="..."))
    # Nên không cần add_conditional_edges ở đây cho Supervisor.
    
    # Tuy nhiên, sau khi các Wrapper hoàn thành, chúng cần trả quyền điều khiển về Supervisor
    workflow.add_edge("sql_wrapper", "supervisor")
    workflow.add_edge("analyst_wrapper", "supervisor")
    
    # Writer là node tổng hợp cuối cùng
    workflow.add_edge("writer_node", END)
    
    return workflow