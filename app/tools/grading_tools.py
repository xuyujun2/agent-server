import json
from langchain.tools import tool
from app.services.grading.chinese_grader import grade_chinese
from app.services.grading.math_grader import grade_math

@tool(return_direct=True)
def grade_chinese_tool(answer_text: str, rules: str, student_text: str) -> str:
    """
    批改作文。用户需要批改作文时调用此工具。
    answer_text: 标准答案的OCR识别文字
    rules: 评分规则文字
    student_text: 学生试卷的OCR识别文字
    """
    result = grade_chinese(answer_text, rules, student_text)
    return json.dumps(result, ensure_ascii=False, indent=2)

@tool(return_direct=True)
def grade_math_tool(answer_text: str, rules: str, student_text: str) -> str:
    """
    批改数学作业（数学试卷、计算题、应用题）。用户需要批改数学时调用此工具。
    answer_text: 标准答案的OCR识别文字
    rules: 评分规则文字
    student_text: 学生试卷的OCR识别文字
    """
    result = grade_math(answer_text, rules, student_text)
    return json.dumps(result, ensure_ascii=False, indent=2)
