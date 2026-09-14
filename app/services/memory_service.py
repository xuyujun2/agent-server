# 长期记忆

import json

import redis
from langchain_openai import ChatOpenAI

from app.config import Config


redis_client = redis.Redis.from_url(
    Config.REDIS_URL,
    decode_responses=True,
)

llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.BASE_URL,
    temperature=0,
)


def load_long_term_memory(user_id: str) -> list:
    """读取用户的长期记忆。"""
    # redis_client.smembers(f"long_term_memory:{user_id}") 示例 {"喜欢电子产品的用户", "常用收货地址：北京", "偏好晚上联系"}
    # list(redis_client.smembers(f"long_term_memory:{user_id}")) 示例 ["喜欢电子产品的用户", "常用收货地址：北京", "偏好晚上联系"]
    return list(redis_client.smembers(f"long_term_memory:{user_id}"))


def save_long_term_memory(user_id: str, question: str, answer: str):
    """从本轮对话中提炼并保存长期记忆。"""
    prompt = f"""从下面对话中提取值得长期保存的用户信息。

只提取用户明确说出的身份、偏好、习惯。
不要保存订单状态、价格和临时问题。
输出JSON数组，没有就输出[]。

用户：{question}
助手：{answer}
"""

    # response 示例 ["喜欢电子产品", "收货地址在北京"]
    response = llm.invoke(prompt)

    try:
        memories = json.loads(response.content)
    except Exception:
        return

    for item in memories:
        # 追加长期记忆  sadd：把元素加入集合，自动去重。
        redis_client.sadd(f"long_term_memory:{user_id}", item)


def build_long_term_memory(user_id: str) -> str:
    memories = load_long_term_memory(user_id)
    if not memories:
        return "暂无"
    return "\n".join(memories)
