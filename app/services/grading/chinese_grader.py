import json
from langchain_openai import ChatOpenAI
from app.config import Config

# 初始化文本模型（作文批改）
llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.BASE_URL,
    temperature=0.3,
    max_tokens=2000
)

DEFAULT_CHINESE_RULES = """
默认评分规则：
1. 主题明确（25分）：中心突出，不跑题
2. 结构完整（25分）：开头、主体、结尾清晰连贯
3. 语言表达（30分）：语句通顺，用词准确，无病句
4. 内容充实（20分）：素材具体，论证充分，不空洞
5. 每3个错别字扣2分，字数每少50字扣5分
"""

def grade_chinese(answer_text: str, rules: str, student_text: str) -> dict:
    """
    批改作文
    """
    if rules is None or rules.strip() == "":
        rules = DEFAULT_CHINESE_RULES
        
    content = f"""你是一位作文老师，根据OCR识别结果和评分规则批改学生作文。

标准答案识别结果：
{answer_text}

学生试卷识别结果：
{student_text}

评分规则：
{rules}

输出格式要求：
1. 根据标准答案批改
2. 从主题、结构、语言、内容四个维度评分
3. 指出优点和不足
4. 输出JSON格式：
{{
    "subject": "作文",
    "total_score": 总分,
    "dimensions": {{
        "主题": 分数,
        "结构": 分数,
        "语言": 分数,
        "内容": 分数
    }},
    "questions": [
        {{
            "number": "作文",
            "score": 总分,
            "is_correct": false,
            "feedback": "作文批改说明"
        }}
    ],
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": "改进建议"
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
