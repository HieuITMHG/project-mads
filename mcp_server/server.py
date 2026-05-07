from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

mcp =  FastMCP("MADS",
               transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=["localhost:*", "127.0.0.1:*", "mcp_server:*"],
                allowed_origins=["http://localhost:*", "mcp_server:*"],
            ))