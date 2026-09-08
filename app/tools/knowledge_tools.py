from langchain.tools import tool
from pydantic import BaseModel, Field
from langchain_community.vectorstores import Chroma
from datetime import datetime, timedelta

from build_kb import get_embeddings, VECTOR_DIR

# 这些类型需要按文件日期做过期过滤
TIME_SENSITIVE_TYPES = ["return_policy", "shipping_policy", "price_policy", "promotion_policy"]


class SearchKnowledgeInput(BaseModel):
    question: str = Field(description="用户询问的公司介绍、发货规则、退货政策等问题")


@tool(args_schema=SearchKnowledgeInput)
def search_knowledge(question: str) -> str:
    """查询公司知识库。用户询问公司资料、业务规则或常见问题时调用。"""
    vector_store = Chroma(
        persist_directory=VECTOR_DIR,
        embedding_function=get_embeddings(),
    )
    docs = vector_store.similarity_search(question, k=30)

    if not docs:
        return "知识库中没有找到相关内容"

    # 文件创建日期在文件名上，超过 3 年的时效类文档视为失效，过滤掉
    cutoff = datetime.now() - timedelta(days=365 * 3)
    result = []
    for doc in docs:
        doc_type = doc.metadata.get("type")
        if doc_type in TIME_SENSITIVE_TYPES:
            doc_date = doc.metadata.get("date")
            if doc_date and doc_date != "未知":
                try:
                    if datetime.strptime(doc_date, "%Y-%m-%d") < cutoff:
                        continue
                except ValueError:
                    pass
        result.append(doc)

    if not result:
        return "知识库中没有找到相关内容"
    return "\n\n".join(doc.page_content for doc in result)
