from api.agents.state import AgentState
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from api.agents.nodes import agent_reasoning_node, get_tools

def build_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_reasoning_node)
    workflow.add_node("tools", ToolNode(get_tools()))
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")
    
    return workflow