from api.agents.tools.rag import search_rag
import core.checkpointer as cp
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from core.config import settings
from api.agents.olist_schema import OLIST_DB_SCHEMA

def get_tools():
    return [search_rag] + cp.dynamic_mcp_tools

BASE_SYSTEM_PROMPT = """You are MADS (Masterful Analytics & Data Science Assistant), an expert data analyst and database engineer. 
You are assisting a user in analyzing the Olist E-commerce dataset and other business documents.

You have access to the following tools:
1. 'search_rag': To retrieve context and information from user-uploaded text documents (PDFs, Docx).
2. 'execute_sql': To query the PostgreSQL database (strictly use SELECT statements).
3. 'run_python': To execute Python code in a secure sandbox for complex pandas data manipulation, statistical calculations, or generating charts.

CRITICAL INSTRUCTIONS:
1. DATA ACCURACY: NEVER hallucinate data, metrics, or column names. Always use the 'execute_sql' or 'run_python' tools to fetch real data before answering.
2. HANDLING ERRORS: If a tool returns an error, DO NOT panic. Read the error message, correct your code, and call the tool again.
3. VISUALIZATION (PLOTLY RULE): If the user asks for a chart/graph, you MUST strictly use the `plotly.express` or `plotly.graph_objects` library. Do NOT use `fig.show()`. Instead, extract the JSON representation using `fig.to_json()`, WRAP it in a `print()` call: `print(fig.to_json())`. In your final response, wrap the EXACT printed JSON string inside <CHART_JSON>...</CHART_JSON> tags.
   - ABSOLUTE RULE: You may ONLY include <CHART_JSON> in your response if the tool's Execution results literally contain the chart JSON string. If the tool returned a WARNING about empty output, you MUST fix your code and call the tool again — NEVER invent or fabricate chart JSON from memory.
4. CRITICAL: You are writing a standard Python script, NOT a Jupyter Notebook. You MUST explicitly use `print()` statements to output your final answers or data summaries. If you don't use `print()`, you will receive an empty output and MUST rewrite the code.
5. TABLE STRUCTURE: Pay attention to the relationships between tables in the Olist Database.

LANGUAGE RULE: 
You must perform all reasoning, coding, and database querying in English, formatted cleanly using Markdown.
"""

async def agent_reasoning_node(state: dict, config: RunnableConfig):
    print("Agent đang suy nghĩ")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0
    )

    llm_with_tools = llm.bind_tools(get_tools())

    file_context = state.get("file_context", "")

    dynamic_system_prompt = f"""{BASE_SYSTEM_PROMPT}

    ---
    [OLIST DATABASE SCHEMA]
    {OLIST_DB_SCHEMA}

    ---
    [USER UPLOADED FILES CONTEXT]
    {file_context if file_context else "No external files uploaded in this session."}
    """

    messages = [SystemMessage(content=dynamic_system_prompt)] + state["messages"]

    response = await llm_with_tools.ainvoke(messages, config)

    return {"messages": [response]}