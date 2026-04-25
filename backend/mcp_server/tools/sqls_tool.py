from mcp_server.server import mcp
from mcp_server.database import get_db_readonly
from sqlalchemy import text

@mcp.tool()
def execute_readonly_sql(query: str) -> str:
    """Thực thi lệnh SQL an toàn trên DB Olist."""
    db_gen = get_db_readonly()
    db = next(db_gen)
    try:
        result = db.execute(text(f"SELECT * FROM ({query}) AS sub LIMIT 100"))
        rows = result.fetchall()
        return str(rows)
    except Exception as e:
        return f"Lỗi SQL: {str(e)}"
    finally:
        db.close()
    