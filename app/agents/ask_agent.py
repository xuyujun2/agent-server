import asyncio
import json

from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_message_histories import RedisChatMessageHistory

from app.config import Config
from app.tools.order_tools import build_order_tools
from app.tools.knowledge_tools import search_knowledge
from app.services.memory_service import build_long_term_memory, save_long_term_memory
from app.utils.logger import logger

MAX_OUTPUT_ATTEMPTS = 3


class CustomerAnswer(BaseModel):
    answer: str


# class 定义的类，不能直接作为变量传进提示词，需要处理后，再传入
OUTPUT_SCHEMA = json.dumps(CustomerAnswer.model_json_schema(), ensure_ascii=False)


async def validate_answer(raw_output: str) -> str:
    """只修正最终回复格式，不重新执行可能写入数据库的工具。"""
    for attempt in range(1, MAX_OUTPUT_ATTEMPTS + 1):
        try:
            data = json.loads(raw_output)
            result = CustomerAnswer(**data)
            answer = result.answer.strip()
            if not answer:
                raise ValueError("answer 不能为空")
            return answer
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            logger.warning("客服回复格式校验失败，第%s/%s次：%s", attempt, MAX_OUTPUT_ATTEMPTS, exc)
            if attempt == MAX_OUTPUT_ATTEMPTS:
                return "系统暂时无法生成回复，请稍后重试。"
            response = await llm.ainvoke([
                ("system", f"上次输出格式不对。请按以下 JSON Schema 重新输出，不要输出其他内容：{OUTPUT_SCHEMA}"),
                ("human", raw_output),
            ])
            raw_output = response.content


# 初始化模型
# llm = ChatOpenAI(...) 写在文件开头，整个程序启动时创建一次，所有请求共用这一个对象。每次不重新请求“加载模型”  
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    temperature=0.3,
    base_url=Config.BASE_URL,  # deepseek的 API key，先测试用，后面要改成 OpenAI Platform 的 API key
    timeout=Config.LLM_TIMEOUT,
    max_retries=Config.LLM_MAX_RETRIES,
)

def get_chat_history(user_id: str):
    """获取指定用户保存在 Redis 中的聊天记录。"""
    return RedisChatMessageHistory(
        session_id=user_id,  # RedisChatMessageHistory 内部会用 session_id 做存储消息的 key
        url=Config.REDIS_URL,
        ttl=86400 * 7,  # 这里，7天过期，7天没活动，就删除历史记录; Redis删了，长期记忆还在
    )

# 提示词模板   long_term_memory: 长期记忆      chat_history: 短期记忆
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的电商客服助手。你的职责：
1. 帮用户查询订单信息
2. 帮用户申请退货退款

规则：
- 查询订单用 query_order 工具
- 查用户所有订单用 query_my_orders 工具
- 退货用 apply_return 工具，需要订单号和原因
- 订单和退货工具只查询当前用户的数据，不使用用户问题中提到的其他用户ID
- 如果用户没给订单号，先问他要
- 保持礼貌、专业

常见场景示例：

示例1：用户提供了订单号
用户：帮我查询订单 ORD20260805001
正确做法：立即调用 query_order，参数 order_no="ORD20260805001"。
禁止：继续询问用户ID。

示例2：用户先说查订单，后来补充订单号
用户：帮我查询订单状态
助手：请提供订单号。
用户：ORD20260805001
正确做法：结合上一轮对话，立即调用 query_order。
禁止：忘记上一轮对话，或继续询问用户ID。

示例3：用户要查询自己名下的全部订单
用户：查询我的所有订单，我的用户ID是 user_001
正确做法：调用 query_my_orders。
禁止：调用 query_order。

示例4：用户只说查询名下全部订单
用户：查询我的所有订单
正确做法：调用 query_my_orders，不需要向用户追问。

示例5：用户同时提供订单号和用户ID，但只要求查某个订单
用户：订单号 ORD20260805001，用户ID user_001，帮我查订单状态
正确做法：调用 query_order，参数 order_no="ORD20260805001"。
禁止：因为看到用户ID就调用 query_my_orders。

示例6：用户申请退货，且信息完整
用户：我要退掉订单 ORD20260805001，原因是商品损坏，我的用户ID是 user_001
正确做法：调用 apply_return，参数 order_no="ORD20260805001"、reason="商品损坏"。

示例7：退货信息不完整
用户：我要退掉订单 ORD20260805001
正确做法：询问退货原因。
禁止：缺少参数时直接调用 apply_return。

示例8：订单不存在
用户：查询订单 ORD99999999999
正确做法：调用 query_order。工具返回未找到后，如实告诉用户。
禁止：自己编造商品、价格和订单状态。

示例9：用户只是咨询退货规则
用户：买了多久不能退货？
正确做法：直接说明规则。
禁止：用户没有明确申请退货时调用 apply_return。

示例10：工具返回什么就回答什么
工具返回：未找到该订单，请确认订单号是否正确
正确回答：未找到该订单，请确认订单号是否正确。
禁止：修改工具结果或捏造订单信息。"""),
    ("system", "已知用户长期信息：\n{long_term_memory}"),
    ("system", "最终回复请按以下 JSON Schema 输出，不要输出其他内容：{output_schema}。调用工具时仍正常传入工具参数。"),
    ("placeholder", "{chat_history}"),
    # ("system",""""""),
    # ("human", "{input}"),
    ("human", """给用户的回答内容先加一句 "nice to meet y!"，然后再回答用户问题。

聊天记录只用于理解上下文，不能作为当前订单状态。
查询订单、申请退货，必须重新调用工具，查询最新结果，用最新结果覆盖历史记录。
查询公司资料、规则或条款时，每次都必须调用 search_knowledge 重新查询。
用户追问“第几条、上一条、下一条”时，要结合聊天记录补全问题后再查询，禁止直接根据历史回答猜测。

用户问题：{input}"""),
    ("placeholder", "{agent_scratchpad}")
])

def create_agent_executor(user_id: str):
    """为每个用户创建独立的Agent执行器（含记忆）"""
    memory = get_chat_history(user_id)
    tools = [*build_order_tools(user_id), search_knowledge]

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        # verbose=True,
        max_iterations=5,
        handle_parsing_errors=True
    )
    
    async def run(question: str):
        logger.info(f"用户 {user_id} 提问：{question}")

        # RedisChatMessageHistory 是同步接口，放到线程池中执行，避免阻塞事件循环。
        chat_history = await asyncio.to_thread(lambda: memory.messages[-10:])
        long_term_memory = await asyncio.to_thread(build_long_term_memory, user_id)

        result = await executor.ainvoke({
            "input": question,
            "chat_history": chat_history,
            "long_term_memory": long_term_memory,
            "output_schema": OUTPUT_SCHEMA,
        })
        answer = await validate_answer(result["output"])

        await asyncio.to_thread(memory.add_user_message, question)
        await asyncio.to_thread(memory.add_ai_message, answer)
        await asyncio.to_thread(save_long_term_memory, user_id, question, answer)
        logger.info(f"用户 {user_id} 回复：{answer}")
        return answer
    
    # return run
    # 返回字典，包含 run 函数和 memory 对象
    return {
        "run": run,
        "memory": memory
    }
