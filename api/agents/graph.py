from api.agents.state import AgentState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from api.agents.nodes import agent_reasoning_node, get_tools, manage_memory_node

def build_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("manage_memory", manage_memory_node)
    workflow.add_node("agent", agent_reasoning_node)
    workflow.add_node("tools", ToolNode(get_tools()))
    
    workflow.add_edge(START, "manage_memory")
    workflow.add_edge("manage_memory", "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "manage_memory")
    
    return workflow