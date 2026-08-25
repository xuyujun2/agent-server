from fastapi import APIRouter, UploadFile, File
from starlette.concurrency import run_in_threadpool
from app.services.report_service import analyze_pdf
import os
import shutil
import tempfile

router = APIRouter(prefix="/report", tags=["财报分析"])

# 定义一个路径
UPLOAD_DIR = "uploads"
# 创建文件夹
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze")
# file是字段名，UploadFile 是类型，默认是一个必填的文件，File是文件  (...) 是必填，如果如果请求没带这个文件就报错
async def analyze_report(file: UploadFile = File(...)):
    """上传PDF，返回分析报告"""
    # 在 UPLOAD_DIR 目录下，生成临时文件，文件名随机，为了 避免原文件名冲突（多人同时上传同名文件会覆盖）
    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=".pdf",
        dir=UPLOAD_DIR,
        delete=False,
    ) as f:
        file_path = f.name
        # shutil：Python 文件操作工具库（复制、移动、删除等）       file.file：文件里的数据
        shutil.copyfileobj(file.file, f)
    
    try:
        # PDF解析和大模型调用是同步任务，放入线程池避免阻塞其他接口
        result = await run_in_threadpool(analyze_pdf, file_path)
        return {"code": 0, "data": result}
    except Exception as e:
        return {"code": 1, "msg": str(e)}
    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)
