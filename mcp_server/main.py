from mcp_server.server import mcp

import mcp_server.tools.sqls_tool
import mcp_server.tools.codes_tool
import mcp_server.resources.db_schemas

if __name__ == "__main__":
    print(f"🚀 Khởi động MADS MCP Server ...")

    mcp.settings.port = 8001
    mcp.settings.host = "0.0.0.0"
    
    mcp.run(
        transport="sse",
    )