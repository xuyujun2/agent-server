"""本地 stdio MCP 服务。"""

import json

from mcp.server.fastmcp import FastMCP

from code_agent_service import code_agent


mcp = FastMCP("code-agent")


@mcp.tool()
def generate_code(requirement: str) -> str:
    """根据需求生成可运行的 Python 代码，并自动执行和修正。"""
    result = code_agent(requirement, mode="code")
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def generate_test(function_code: str) -> str:
    """为给定的 Python 函数生成并执行单元测试。"""
    result = code_agent(function_code, mode="test")
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
