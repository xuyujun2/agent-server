# 这个文件没用了


# stdio 通信，用于本地

import asyncio
import json
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from code_agent_service import code_agent

# 创建 MCP Server
server = Server("code-agent")

# 注册两个工具
@server.list_tools()
# handle_list_tools()：函数名     -> list[types.Tool]：返回类型 lsit列表、数组  返回一个列表，列表里装的都是工具对象（types.Tool）
async def handle_list_tools() -> list[types.Tool]:
    return [
        # types.Tool()：调用 MCP 库里的 Tool 类，创建一个工具对象
        types.Tool(
            # 工具名
            name="generate_code",
            # 描述（工具级别）
            description="根据需求生成可运行的Python代码，自动执行验证，报错则自动修正",
            # inputSchema：定义工具需要什么参数   type": "object" 参数是一个对象（JSON 对象）  properties：对象里有哪些字段
            # requirement 是字段   "type": "string" 是指 字段 requirement 是个字符串      "description": "代码需求描述" 是指 requirement 这个字段是干什么的（参数级别）
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement": {"type": "string", "description": "代码需求描述"},
                },
                # 调用时必须传 requirement 这个参数
                "required": ["requirement"],
            },
        ),
        types.Tool(
            name="generate_test",
            description="针对给定的Python函数自动生成单元测试，并执行验证",
            inputSchema={
                "type": "object",
                "properties": {
                    "function_code": {"type": "string", "description": "要测试的Python函数代码"},
                },
                "required": ["function_code"],
            },
        ),
    ]

# 执行 Tool
@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "generate_code":
        requirement = arguments.get("requirement")
        if not requirement:
            # types.TextContent() 用MCP的方式把它包装成文本，方便 AI 接收。
            return [types.TextContent(type="text", text="错误：缺少 requirement 参数")]
        
        result = code_agent(requirement, mode="code")
        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
            # text=result.get("code", "")
        )]
    
    elif name == "generate_test":
        function_code = arguments.get("function_code")
        if not function_code:
            return [types.TextContent(type="text", text="错误：缺少 function_code 参数")]
        
        result = code_agent(function_code, mode="test")
        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
    
    else:
        return [types.TextContent(type="text", text=f"未知工具: {name}")]

# 启动 MCP Server（通过 stdio）
async def main():
    # 通过标准输入/输出建立MCP通信通道
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        # 启动MCP服务器
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="code-agent",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
