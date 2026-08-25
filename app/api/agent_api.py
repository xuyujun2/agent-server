import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse  # FastAPI 的流式响应，用于实现 SSE
from app.models.schemas import AskRequest
from app.agents.ask_agent import create_agent_executor
from app.utils.logger import logger

router = APIRouter(prefix="/agent", tags=["客服"])

# 存储每个用户的执行器（简单版，实际可用Redis）
sessions = {}

@router.post("/ask")
def ask(request: AskRequest):
    """客服对话接口"""
    try:
        # 获取或创建用户的Agent执行器
        if request.user_id not in sessions:
            sessions[request.user_id] = create_agent_executor(request.user_id)
        
        # 从字典里取 run 函数执行
        agent_wrapper = sessions[request.user_id]
        answer = agent_wrapper["run"](request.question)
        return {"code": 0, "data": {"answer": answer}}
    
    except Exception as e:
        logger.error(f"客服接口异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
async def ask_stream(request: AskRequest):
    """SSE 流式客服对话接口：把完整答案逐字发给前端。"""

    if request.user_id not in sessions:
        sessions[request.user_id] = create_agent_executor(request.user_id)

    # sessions[request.user_id] => { "run": run, "memory": memory }
    agent_wrapper = sessions[request.user_id]

    # 获取模型回答，把回答逐个生成文字
    async def event_stream():
        try:
            # 先告诉前端：本次流式回答已经开始    _sse_event("start") 生成 data: {"type":"start","content":""}\n\n
            yield _sse_event("start")

            # 执行了agent函数，传递了 request.question，同时把函数 agent 放到独立线程执行，避免阻塞 FastAPI 的事件循环。
            # answer = await asyncio.to_thread(agent, request.question)
            answer = await asyncio.to_thread(agent_wrapper["run"], request.question)

            for char in answer:
                # yield 是生成器，每次返回一个数据块并暂停，供 StreamingResponse 逐块发送给前端。
                yield _sse_event("content", char)
                # 每个字间隔 0.02 秒，让前端显示出打字效果
                await asyncio.sleep(0.02)

            # 告诉前端：本次回答已经全部发送完成
            yield _sse_event("done")
        except Exception as e:
            # 流式过程中出错时，记录日志，并把错误事件发给前端
            logger.error(f"SSE客服接口异常: {str(e)}")
            yield _sse_event("error", str(e))

    # StreamingResponse：流式响应，边生成数据边发给前端，不用等完整结果。
    # text/event-stream 是 SSE 规定 服务端把数据以流形式响应给前端
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            # 不缓存流式回答，并禁止代理服务器把小段数据合并后再发送
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, content: str = "") -> str:
    """SSE 数据格式化：每条消息必须以 data: 开头，并以两个换行结束。"""
    data = json.dumps(
        {"type": event_type, "content": content},
        # 保留中文原文，不转成 \u4f60\u597d 这种 Unicode 转义形式
        ensure_ascii=False,
    )
    # `\n\n` 是 **SSE 协议规定的消息结束符**
    return f"data: {data}\n\n"


@router.get("/history")
def get_history(user_id: str):
    """获取用户聊天历史"""
    if user_id not in sessions:
        return {"code": 0, "data": {"history": []}}
    
    # 从字典里取 memory 对象，取 messages
    memory = sessions[user_id]["memory"]
    history = [
        {"role": msg.type, "content": msg.content}
        for msg in memory.messages
    ]
    return {"code": 0, "data": {"history": history}}
