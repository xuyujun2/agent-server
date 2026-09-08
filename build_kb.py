"""
build_kb.py — 知识库建库脚本
用法:
  首次建库(读整个目录): python build_kb.py --mode init --dir data/knowledge
  新增单个文件:          python build_kb.py --mode add --file "data/knowledge/退货政策/2025-08-01.pdf"
  
  修改知识库文件后，先删除旧库，再重建：
  Remove-Item -Recurse -Force ./data/vector_store
  python build_kb.py --mode init --dir data/knowledge

  追加文件，其实也可以这么做，先删除旧库，再重建，不用在代码上区分初始创建或追加

  知识库存到向量库步骤：读取 - 打元数据标签(date、source、type) - 切片 -入库 - 检索
"""
import argparse
import os
import re

from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# 向量库的持久化存储目录
VECTOR_DIR = "./data/vector_store"

def get_embeddings():
    """创建向量模型。"""

    return OpenAIEmbeddings(
        api_key=os.getenv("VISION_API_KEY"),
        base_url=os.getenv("EMBEDDING_BASE_URL"),
        model=os.getenv("EMBEDDING_MODEL"),
        check_embedding_ctx_length=False,
        chunk_size=10,
    )

def get_doctype(file_path: str) -> str:
    """按文件路径 判断资料类别，返回稳定 type 值"""
    path = file_path
    if "退货" in path or "退款" in path or "换货" in path:
        return "return_policy"
    if "物流" in path or "发货" in path:
        return "shipping_policy"
    if "价格" in path or "费用" in path or "运费" in path:
        return "price_policy"
    if "活动" in path or "大促" in path:
        return "promotion_policy"
    if "FAQ" in path.upper():
        return "faq"
    if "手册" in path or "说明" in path:
        return "product_manual"
    return "general"


def tag_docs(docs, file_path: str):
    """给每个 Document 打 date/type/source 标签，强时效资料靠这些字段过滤"""
    # 从文件名提取日期，形如 2025-08-01
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", file_path)
    doc_date = date_match.group() if date_match else "未知"
    doc_type = get_doctype(file_path)

    for d in docs:
        d.metadata["date"] = doc_date
        d.metadata["type"] = doc_type
        d.metadata["source"] = d.metadata.get("source", file_path)
    return docs

# kb_dir 知识库所在目录   root是文件的直接父级目录   files是文件
def init_index(kb_dir: str):
    """首次建库：读目录下所有 pdf/txt，切块，一次性建库"""
    all_docs = []
    for root, _, files in os.walk(kb_dir):
        for f in files:
            path = os.path.join(root, f)
            if f.endswith(".pdf"):
                docs = PyPDFLoader(path).load()
            elif f.endswith(".txt"):
                docs = TextLoader(path, encoding="utf-8").load()
            else:
                continue
            # 打 date/type 标签
            docs = tag_docs(docs, path)

            # 合并 docs，追加到 all_docs 末尾
            all_docs.extend(docs)

    if not all_docs:
        print("[失败] 目录下没有 pdf/txt 文件")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(all_docs)

    # 存到向量库
    Chroma.from_documents(
        chunks,
        embedding=get_embeddings(),
        persist_directory=VECTOR_DIR,
    )
    print(f"[建库完成] 库目录: {VECTOR_DIR}")


def add_doc(file_path: str):
    """新增单个文件：先查重，再读、切、追加进已有库"""
    if not os.path.exists(file_path):
        print(f"[失败] 文件不存在: {file_path}")
        return
    if not os.path.exists(VECTOR_DIR):
        print("[失败] 向量库不存在，请先执行 --mode init")
        return

    # 打开已有库
    vector_store = Chroma(
        persist_directory=VECTOR_DIR,
        embedding_function=get_embeddings(),
    )

    # 按 metadata 里的 source 查重，向量库中已有该文件，则跳过
    existing = vector_store.get(where={"source": file_path})
    if existing.get("ids"):
        print(f"[跳过] 该文件已入库: {file_path}")
        return

    # 读文件
    if file_path.endswith(".pdf"):
        docs = PyPDFLoader(file_path).load()
    elif file_path.endswith(".txt"):
        docs = TextLoader(file_path, encoding="utf-8").load()
    else:
        print(f"[失败] 仅支持 pdf/txt: {file_path}")
        return

    # 打 date/type 标签
    docs = tag_docs(docs, file_path)
        
    # 切块
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"[切块] 共 {len(chunks)} 块")

    # 追加入库
    vector_store.add_documents(chunks)
    print("[追加完成]")


if __name__ == "__main__":
    # 跑脚本时用 --xxx 值 传参，代码里用 args.xxx 读。
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["init", "add"], required=True)
    # help 就是写给人看的注释，不参与代码逻辑，只有敲 --help 时才显示
    parser.add_argument("--dir", help="init 模式: 知识库目录")
    parser.add_argument("--file", help="add 模式: 要追加的文件路径")
    args = parser.parse_args()

    if args.mode == "init" and args.dir:
        init_index(args.dir)
    elif args.mode == "add" and args.file:
        add_doc(args.file)
    else:
        print("参数不完整。")
