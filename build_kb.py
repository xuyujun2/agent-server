"""
build_kb.py — 知识库建库脚本
用法:
  首次建库(读整个目录): python build_kb.py --mode init --dir data/knowledge
  新增单个文件:          python build_kb.py --mode add --file "data/knowledge/退货政策/2025-08-01.pdf"
"""
import argparse
import os

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings

# 向量库的持久化存储目录
VECTOR_DIR = "./data/vector_store"

def get_embeddings():
    """创建向量模型。"""

    return OpenAIEmbeddings(
        api_key=os.getenv("VISION_API_KEY"),
        base_url=os.getenv("EMBEDDING_BASE_URL"),
        model=os.getenv("EMBEDDING_MODEL"),
    )

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
                docs = TextLoader(path).load()
            else:
                continue
            # 可选：给每个文件打 date/type 标签，需要的话在这里按文件名解析
            all_docs.extend(docs)
            print(f"[读入] {path} -> {len(docs)} 个 Document")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(all_docs)
    print(f"[切块] 共 {len(chunks)} 块")

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
        embedding=get_embeddings(),
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
        docs = TextLoader(file_path).load()
    else:
        print(f"[失败] 仅支持 pdf/txt: {file_path}")
        return
    print(f"[读入] {file_path} -> {len(docs)} 个 Document")

    # 切块
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"[切块] 共 {len(chunks)} 块")

    # 追加入库
    vector_store.add_documents(chunks)
    print("[追加完成]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["init", "add"], required=True)
    parser.add_argument("--dir", help="init 模式: 知识库目录")
    parser.add_argument("--file", help="add 模式: 要追加的文件路径")
    args = parser.parse_args()

    if args.mode == "init" and args.dir:
        init_index(args.dir)
    elif args.mode == "add" and args.file:
        add_doc(args.file)
    else:
        print("参数不完整。")
