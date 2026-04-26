from mcp_server.server import mcp
import httpx

@mcp.tool()
async def run_data_analysis(code: str) -> str:
    """Thực thi mã Python để phân tích dữ liệu và vẽ biểu đồ."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "http://sandbox_api:8002/execute",
            json={"code": code}
        )
    
    res = response.json()
    msg = f"Kết quả thực thi:\n{res['logs']}"
    if res['files']:
        msg += f"\nCác file đã sinh ra: {', '.join(res['files'])}"
    return msg
    