from langchain.tools import tool
from langchain.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from datetime import datetime, timedelta
import jieba

from build_kb import get_embeddings, VECTOR_DIR

# 这些类型需要按文件日期做过期过滤
TIME_SENSITIVE_TYPES = ["return_policy", "shipping_policy", "price_policy", "promotion_policy"]
USE_RERANKER = False  # True：使用重排序；False：不使用重排序


class SearchKnowledgeInput(BaseModel):
    question: str = Field(description="用户询问的公司介绍、发货规则、退货政策等问题")


_retriever = None


def create_retriever():
    """创建 BM25 + 向量检索 + 重排序检索器。"""

    # 加载向量库
    vector_store = Chroma(
        persist_directory=VECTOR_DIR,
        embedding_function=get_embeddings(),
    )

    # vector_store.get() 返回的 data 里，文本块内容字段名是 "documents"，不是 "page_content"
    data = vector_store.get(include=["documents", "metadatas"])
    documents = [
        Document(page_content=text, metadata=metadata or {})
        for text, metadata in zip(data["documents"], data["metadatas"])
    ]

    #  BM25建库/创建检索器
    bm25_retriever = BM25Retriever.from_documents(
        documents,
        preprocess_func=lambda text: list(jieba.cut_for_search(text)),
    )
    bm25_retriever.k = 10

    # 创建向量检索器     as_retriever() 检索时内部会调用 similarity_search
    vector_retriever = vector_store.as_retriever(search_kwargs={"k": 10})

    # 多路召回：合并向量检索、BM25检索
    hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.5, 0.5],
    )

    # 暂时不用重排序，因为会慢
    if not USE_RERANKER:
        return hybrid_retriever

    # 创建 北京智源人工智能研究院 模型 BAAI
    reranker_model = HuggingFaceCrossEncoder(
        model_name="BAAI/bge-reranker-base"
    )

    # 创建排序器
    reranker = CrossEncoderReranker(model=reranker_model, top_n=3)

    # 合并排序器和多路召回检索器
    return ContextualCompressionRetriever(
        base_retriever=hybrid_retriever,
        base_compressor=reranker,
    )


def get_retriever():
    """只创建一次检索器，避免每次提问都重新加载模型。"""
    global _retriever
    if _retriever is None:
        _retriever = create_retriever()
    return _retriever


@tool(args_schema=SearchKnowledgeInput)
def search_knowledge(question: str) -> str:
    """查询公司知识库。用户询问公司资料、业务规则或常见问题时调用。"""
    docs = get_retriever().invoke(question)

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
