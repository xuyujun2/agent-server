# 高并发程度很大时，使用这个 redis.asyncio 保存和读取缓存

# import json
#
# from langchain_core.messages import (
#     AIMessage,
#     BaseMessage,
#     HumanMessage,
#     message_to_dict,
#     messages_from_dict,
# )
# from redis.asyncio import Redis
#
# from app.config import Config
#
#
# redis_client = Redis.from_url(Config.REDIS_URL, decode_responses=True)
#
#
# class AsyncRedisChatMessageHistory:
#     """使用 redis.asyncio 原生异步保存和读取聊天记录。"""
#
#     def __init__(self, session_id: str, ttl: int = 86400 * 7):
#         self.key = f"message_store:{session_id}"
#         self.ttl = ttl
#
#     async def aget_messages(self) -> list[BaseMessage]:
#         """异步读取聊天记录。"""
#         items = await redis_client.lrange(self.key, 0, -1)
#         return messages_from_dict([json.loads(item) for item in reversed(items)])
#
#     async def aadd_message(self, message: BaseMessage):
#         """异步保存一条聊天记录，并刷新过期时间。"""
#         pipe = redis_client.pipeline()
#         pipe.lpush(self.key, json.dumps(message_to_dict(message), ensure_ascii=False))
#         pipe.expire(self.key, self.ttl)
#         await pipe.execute()
#
#     async def aadd_user_message(self, content: str):
#         """异步保存用户消息。"""
#         await self.aadd_message(HumanMessage(content=content))
#
#     async def aadd_ai_message(self, content: str):
#         """异步保存模型回复。"""
#         await self.aadd_message(AIMessage(content=content))
