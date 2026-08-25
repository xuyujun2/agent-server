from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from app.config import Config
from app.tools.grading_tools import grade_chinese_tool, grade_math_tool

llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.BASE_URL,
    temperature=0.3
)

tools = [grade_chinese_tool, grade_math_tool]

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个作业批改助手。

规则：
1. 根据标准答案和学生试卷的OCR识别文字判断是作文还是数学
2. 作文调用 grade_chinese_tool
3. 数学、计算题、应用题调用 grade_math_tool
4. 必须把完整的标准答案识别文字、评分规则和学生试卷识别文字传给工具
5. 工具返回什么JSON，你就原样返回什么JSON，不要添加说明或Markdown
6. 无法判断学科类型或信息不全时，说明原因"""),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

def create_agent():
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=3,
        handle_parsing_errors=True
    )
    return executor

executor = create_agent()
