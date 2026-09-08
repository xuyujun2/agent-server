from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_message_histories import RedisChatMessageHistory

from app.config import Config
from app.tools.order_tools import query_order, query_my_orders, apply_return
from app.utils.logger import logger

# 初始化模型
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    temperature=0.3,
    base_url=Config.BASE_URL  # deepseek的 API key，先测试用，后面要改成 OpenAI Platform 的 API key
)

# 工具列表
tools = [query_order, query_my_orders, apply_return]


def get_chat_history(user_id: str):
    """获取指定用户保存在 Redis 中的聊天记录。"""
    return RedisChatMessageHistory(
        session_id=user_id,
        url=Config.REDIS_URL,
        ttl=86400 * 7,
    )

# 提示词模板
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个专业的电商客服助手。你的职责：
1. 帮用户查询订单信息
2. 帮用户申请退货退款

规则：
- 查询订单用 query_order 工具
- 查用户所有订单用 query_my_orders 工具
- 退货用 apply_return 工具，需要订单号和原因
- 如果用户没给订单号，先问他要
- 保持礼貌、专业

常见场景示例：

示例1：用户提供了订单号
用户：帮我查询订单 ORD20260805001
正确做法：立即调用 query_order，参数 order_no="ORD20260805001"
禁止：继续询问用户ID。query_order 只需要订单号。

示例2：用户先说查订单，后来补充订单号
用户：帮我查询订单状态
助手：请提供订单号。
用户：ORD20260805001
正确做法：结合上一轮对话，立即调用 query_order。
禁止：忘记上一轮对话，或继续询问用户ID。

示例3：用户要查询自己名下的全部订单
用户：查询我的所有订单，我的用户ID是 user_001
正确做法：调用 query_my_orders，参数 user_id="user_001"
禁止：调用 query_order。

示例4：用户只说查询名下全部订单
用户：查询我的所有订单
正确做法：询问用户ID。query_my_orders 必须有 user_id 才能调用。

示例5：用户同时提供订单号和用户ID，但只要求查某个订单
用户：订单号 ORD20260805001，用户ID user_001，帮我查订单状态
正确做法：调用 query_order，参数 order_no="ORD20260805001"
禁止：因为看到用户ID就调用 query_my_orders。

示例6：用户申请退货，且信息完整
用户：我要退掉订单 ORD20260805001，原因是商品损坏，我的用户ID是 user_001
正确做法：调用 apply_return，参数 order_no="ORD20260805001"、reason="商品损坏"、user_id="user_001"。

示例7：退货信息不完整
用户：我要退掉订单 ORD20260805001
正确做法：询问退货原因和用户ID。
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
    ("placeholder", "{chat_history}"),
    # ("system",""""""),
    # ("human", "{input}"),
    ("human", """回答前先加一句 "nice to meet you!"，然后再回答用户问题。

聊天记录只用于理解上下文，不能作为当前订单状态。
查询订单、订单列表等数据库信息，必须重新调用工具查询最新结果，禁止直接复制历史回答。

用户问题：{input}"""),
    ("placeholder", "{agent_scratchpad}")
])

def create_agent_executor(user_id: str):
    """为每个用户创建独立的Agent执行器（含记忆）"""
    memory = get_chat_history(user_id)
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        # verbose=True,
        max_iterations=5,
        handle_parsing_errors=True
    )
    
    def run(question: str):
        logger.info(f"用户 {user_id} 提问：{question}")
        result = executor.invoke({
            "input": question,
            "chat_history": memory.messages
        })
        # 保存对话记忆
        memory.add_user_message(question)
        memory.add_ai_message(result["output"])
        logger.info(f"用户 {user_id} 回复：{result['output']}")
        return result["output"]
    
    # return run
    # 返回字典，包含 run 函数和 memory 对象
    return {
        "run": run,
        "memory": memory
    }
