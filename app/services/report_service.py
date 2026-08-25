import pdfplumber
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.config import Config

llm = ChatOpenAI(
    model=Config.MODEL_NAME,
    api_key=Config.OPENAI_API_KEY,
    base_url=Config.BASE_URL
)

def extract_pdf_text(pdf_path: str) -> str:
    """从PDF提取纯文本"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        # 遍历PDF的每一页，pdf.pages 是所有页面的列表
        for page in pdf.pages:
            # 从当前页提取所有文字内容，返回字符串
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_financial_data(text: str) -> str:
    """大模型从财报文本里提取关键数据"""
    prompt = PromptTemplate.from_template("""
从以下财报文本中提取关键数据，输出JSON格式：

{text}

需要提取的字段：
- 营业收入（万元）
- 净利润（万元）
- 总资产（万元）
- 负债率（%）
- 报告期（年份）

只输出JSON，不要解释。
""")
    chain = prompt | llm

    # 切成小块分别提取，再合并结果，因为AI有上下文长度限制，一次处理不了太多
    chunk_size = 6000
    # range(0, len(text), chunk_size)：从0开始，到文本总长度结束，每隔6000个字符取一个数字       text[i:i + chunk_size] 是切片语法  i：起始位置  i + chunk_size：结束位置（不包含）
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    extracted_parts = []
    for chunk in chunks:
        response = chain.invoke({"text": chunk})
        extracted_parts.append(response.content)

    # 只有一段时直接返回；多段时交给模型合并并去重
    if len(extracted_parts) == 1:
        return extracted_parts[0]

    merge_prompt = PromptTemplate.from_template("""
合并以下多段财报数据，去除重复项并解决冲突，输出一个JSON对象：

{data}

只输出JSON，不要解释。
""")
    merge_chain = merge_prompt | llm
    response = merge_chain.invoke({"data": "\n".join(extracted_parts)})
    return response.content

def generate_report(data_json: str) -> str:
    """根据提取的数据生成分析报告"""
    prompt = PromptTemplate.from_template("""
你是一个财务分析师。根据以下数据生成一份简短的分析报告（300字以内）：

{data}

报告格式：
1. 总体概况
2. 关键指标分析
3. 趋势与建议
""")
    chain = prompt | llm
    response = chain.invoke({"data": data_json})
    return response.content

def analyze_pdf(pdf_path: str) -> dict:
    """完整流程：解析PDF → 提取数据 → 生成报告"""
    raw_text = extract_pdf_text(pdf_path)
    if not raw_text.strip():
        raise ValueError("PDF中没有提取到文字，请确认文件不是扫描图片PDF")
    data_json = extract_financial_data(raw_text)
    report = generate_report(data_json)
    return {
        "raw_text": raw_text[:500],
        "extracted_data": data_json,
        "report": report
    }
