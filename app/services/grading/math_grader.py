import json
from langchain_openai import ChatOpenAI
from app.config import Config

# 初始化文本模型（数学批改）
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.BASE_URL,
    temperature=0,
    max_tokens=8000
)

DEFAULT_MATH_RULES = """
默认评分规则：
1. 题目明确写有分值时，以题目分值为准；题目没有写分值时，每题5分
2. 答案正确给满分
3. 答案错误但关键步骤正确，给步骤分（每步1-2分）
4. 完全不会给0分
5. 计算题看过程和结果，选择题只看结果
"""

def grade_math(answer_text: str, rules: str, student_text: str) -> dict:
    """
    批改数学作业
    """

    if rules is None or rules.strip() == "":
        rules = DEFAULT_MATH_RULES
        
    content = f"""你是一位数学老师，根据OCR识别结果和评分规则批改学生数学作业。

标准答案识别结果：
{answer_text}

学生试卷识别结果：
{student_text}

评分规则：
{rules}

批改原则：
- 只要最终答案正确，且步骤逻辑无矛盾，即使解法与参考答案不同，也给满分。
- 步骤分只扣在逻辑错误上，不扣在写法或解法差异上。
- 学生试卷识别文字中只要有答案或解题过程，就属于已经作答，不能判为未作答。
- 只有识别文字中的答题位置确实为空时，才能判为未作答。
- 试卷可能跨页：如果下一页开头出现“学生解”、计算过程或答案，并且在下一道新题之前没有写题号，必须把这些内容归到上一页最后一道题。
- 判断某题未作答前，必须继续检查后续页面；后续页面存在该题的解答过程或答案时，不能判为未作答。
- 比较答案时必须按数学含义判断，不能只比较字符串。忽略空格、括号样式、“和/与/、”等连接写法；多个根或多个答案顺序不同但集合相同，也属于正确。例如“2和3”与“2 和 3”完全相同。
- 批改必须以完整识别文字中的题目、解题过程和最终答案为准，不能只取最后一个数字。例如识别文字写“所以解集为1≤x≤2.5”时，必须按完整解集判断。
- 等值的分数、小数、代数式或方程结果应判为正确；只有数学结果确实不同才能判错。
- 每道题如果写有“每题X分”“本小题X分”或其他明确分值，答对必须得到该题满分，不能套用上一题或上一题型的分值。例如“本小题6分”答对必须给6分。
- 输出前必须逐题核对：is_correct为true时，score应为该题满分；total_score必须等于所有questions中score之和。
- 必须批改学生试卷识别文字中出现的每一道题，questions中不能漏掉任何明确题号。
- 如果标准答案识别结果中缺少某道数学题的答案，必须根据题目自行计算正确答案，再批改学生答案；不能因为标准答案漏识别就判0分。此时feedback必须先写“标准答案无法识别，已自行解题批改”，再写自行计算的正确答案和批改说明。
- 只有题目内容本身残缺到无法理解时，才允许写“无法判断”，并且不得擅自按0分处理。

输出格式要求：
1. 根据标准答案批改
2. 逐题给分，计算总分
3. 指出错误步骤
4. 输出JSON格式：
{{
    "subject": "数学",
    "total_score": 总分,
    "questions": [
        {{
            "number": 题号,
            "student_answer": "学生答案",
            "correct_answer": "正确答案",
            "score": 得分,
            "is_correct": true/false,
            "feedback": "批改说明"
        }}
    ],
    "summary": "整体评价"
}}
只输出JSON，不要其他内容。"""
    
    # 调用 LangChain 的 ChatOpenAI 进行批改
    response = llm.invoke(content)
    
    result_text = response.content
    # 模型偶尔会在JSON外面包一层```json代码块，解析前先去掉。
    result_text = result_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(result_text)
    except:
        return {"raw": result_text, "error": "解析失败"}
