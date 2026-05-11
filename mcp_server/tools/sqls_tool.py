from mcp_server.server import mcp
from mcp_server.database import RO_SessionLocal 
from sqlalchemy import text

@mcp.tool()
async def execute_readonly_sql(query: str) -> str: 
    """
    Execute secure read-only SQL to query Olist ecommerce database.
    IMPORTANT: You must write standard PostgreSQL. 
    Always append LIMIT 100 to your queries unless you are doing a single-row aggregation.
    """
    clean_query = query.strip()
    
    async with RO_SessionLocal() as db:
        try:
            result = await db.execute(text(clean_query))
            
            rows = result.mappings().fetchmany(100)
            print("Kết quả truy vấn")
            print(str([dict(row) for row in rows]))
            return str([dict(row) for row in rows])
        except Exception as e:
            return f"Lỗi SQL: {str(e)}"