from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain.memory import ChatMessageHistory

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
- 保持礼貌、专业"""),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

def create_agent_executor(user_id: str):
    """为每个用户创建独立的Agent执行器（含记忆）"""
    memory = ChatMessageHistory()
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
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
