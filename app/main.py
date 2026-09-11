from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import start_http_server
import threading

from app.api import webhook, agent_api, email_api, report_api, grading_api
from app.tools.knowledge_tools import get_retriever
from app.scheduler.email_scheduler import start_scheduler
from app.utils.logger import logger

app = FastAPI(title="智能客服Agent", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(webhook.router)
app.include_router(agent_api.router)
app.include_router(email_api.router)
app.include_router(report_api.router)
app.include_router(grading_api.router)

#  FastAPI 的启动钩子
@app.on_event("startup")
def start_email_scheduler():
    # 提前在启动服务时，加载重排序模型，否则回答问题时，首次加载这个模型会慢
    # get_retriever()
    # 启动一个新线程，在后台执行 start_scheduler 函数（定时任务，如每30分钟扫描邮件），不阻塞主程序处理请求
    threading.Thread(target=start_scheduler, daemon=True).start()

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # 启动监控
    start_http_server(8001)
    logger.info("监控端口: 8001")
    logger.info("服务启动: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
