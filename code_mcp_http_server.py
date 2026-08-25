# 远程 HTTP MCP 通信

import json

from mcp.server.fastmcp import FastMCP

from code_agent_service import code_agent


# Remote MCP server for production use.
# The local code_mcp_server.py continues to use stdio.
mcp = FastMCP(
    "code-agent-http",
    host="0.0.0.0",
    port=8002,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def generate_code(requirement: str) -> str:
    """Generate and validate Python code."""
    result = code_agent(requirement, mode="code")
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def generate_test(function_code: str) -> str:
    """Generate and run tests for Python code."""
    result = code_agent(function_code, mode="test")
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Remote clients connect to http://SERVER_IP:8002/mcp.
    mcp.run(transport="streamable-http")
