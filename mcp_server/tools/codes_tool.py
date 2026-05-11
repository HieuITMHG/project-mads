from mcp_server.server import mcp
import httpx

@mcp.tool()
async def run_data_analysis(session_id: str, code: str) -> str:
    """
    Execute Python code in a secure sandbox to analyze data and generate charts.
    
    Args:
        session_id: The ID of the current chat session (MUST be extracted from your environment context).
        code: The Python code to execute (e.g., pandas operations, matplotlib/plotly charts).
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "http://sandbox_api:8002/execute",
            json={
                "session_id": session_id,
                "code": code
            }
        )
    
    if response.status_code != 200:
        return f"Error: Sandbox API returned status {response.status_code}. Details: {response.text}"
        
    res = response.json()

    print(f"Response from api: {res}")
    
    if not res.get("success"):
        return f"Execution failed (Crash/Error):\n{res.get('logs') or 'Unknown error — no traceback captured.'}"

    logs = res.get("logs", "").strip()

    if not logs:
        # Empty logs almost always mean the developer forgot print().
        # Return an explicit failure message so the LLM does NOT hallucinate results.
        return (
            "WARNING: Code executed successfully (exit code 0) but produced NO printed output. "
            "This means you forgot to use print() to output results. "
            "DO NOT fabricate any data, chart, or answer based on this empty result. "
            "Rewrite the code and ensure every important value or fig.to_json() call is "
            "wrapped inside a print() statement, then call run_data_analysis again."
        )

    msg = f"Execution results:\n{logs}"

    generated_files = res.get("files", [])
    if generated_files:
        msg += f"\nGenerated files: {', '.join(generated_files)}"

    print(f"Message: {msg}")
        
    return msg