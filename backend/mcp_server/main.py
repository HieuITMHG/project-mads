from mcp_server.server import mcp

import mcp_server.tools.sqls_tool
import mcp_server.resources.db_schemas

if __name__ == "__main__":
    print("🚀 Khởi động MADS MCP Server...")
    mcp.run(transport="sse")