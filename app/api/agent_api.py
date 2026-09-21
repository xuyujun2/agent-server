import asyncio
import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse  # FastAPI 的流式响应，用于实现 SSE
from redis.asyncio import Redis

from app.config import Config
from app.models.schemas import AskRequest
from app.agents.ask_agent import create_agent_executor, get_chat_history
from app.utils.logger import logger
from app.utils.dingtalk_alert import send_dingtalk_alert

router = APIRouter(prefix="/agent", tags=["客服"])
# 限流，服务器层面：每个 Worker 同时最多执行指定数量的 Agent 请求。
agent_semaphore = asyncio.Semaphore(Config.AGENT_MAX_CONCURRENCY)
# 限流，用户层面：接口限流计数保存在 Redis 中，多个 Worker 共享。
rate_limit_redis = Redis.from_url(Config.REDIS_URL, decode_responses=True)


async def check_rate_limit(user_id: str):
    """限制同一用户每分钟调用 Agent 接口的次数。"""
    minute = int(time.time() // 60)  # 当前是第几分钟（时间戳除以60取整，每隔2分钟的话，就 // 120）
    key = f"rate_limit:agent:{user_id}:{minute}"

    # local count = redis.call('INCR', KEYS[1])   key计数+1
    count = await rate_limit_redis.eval(
        """
        local count = redis.call('INCR', KEYS[1])
        if count == 1 then
            redis.call('EXPIRE', KEYS[1], ARGV[1])
        end
        return count
        """,
        1,
        key,
        60,  # 过60秒，自动清空
    )

    if count > Config.AGENT_RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

@router.post("/ask")
async def ask(request: AskRequest):
    """客服对话接口"""
    await check_rate_limit(request.user_id)
    try:
        raise Exception("测试告警")  # 强制触发异常，测试钉钉告警
        
        # Agent 执行器不保存在本地 sessions 中，聊天记录统一从 Redis 读取。
        agent_wrapper = create_agent_executor(request.user_id)
        try:
            await asyncio.wait_for(agent_semaphore.acquire(), 5)
        except TimeoutError:
            return {"code": 1, "msg": "当前咨询人数较多，请稍后再试"}
        try:
            answer = await agent_wrapper["run"](request.question)
        finally:
            agent_semaphore.release()
        return {"code": 0, "data": {"answer": answer}}
    
    except Exception as e:
        logger.error(f"客服接口异常: {str(e)}")
        send_dingtalk_alert(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
async def ask_stream(request: AskRequest):
    """SSE 流式客服对话接口：把完整答案逐字发给前端。"""
    await check_rate_limit(request.user_id)

    # Agent 执行器不保存在本地 sessions 中，支持多 Worker 读取同一份 Redis 记录。
    agent_wrapper = create_agent_executor(request.user_id)

    # 获取模型回答，把回答逐个生成文字
    async def event_stream():
        try:
            # 先告诉前端：本次流式回答已经开始    _sse_event("start") 生成 data: {"type":"start","content":""}\n\n
            yield _sse_event("start")

            # 限流
            try:
                await asyncio.wait_for(agent_semaphore.acquire(), 5)
            except TimeoutError:
                yield _sse_event("error", "当前咨询人数较多，请稍后再试")
                return
            try:
                answer = await agent_wrapper["run"](request.question)
            finally:
                agent_semaphore.release()

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
async def get_history(user_id: str):
    """获取用户聊天历史"""
    memory = get_chat_history(user_id)
    messages = await asyncio.to_thread(lambda: memory.messages)
    history = [
        {"role": msg.type, "content": msg.content}
        for msg in messages
    ]
    return {"code": 0, "data": {"history": history}}
