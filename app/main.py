from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import start_http_server
import threading

from app.api import webhook, agent_api, email_api, report_api, grading_api
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

# FastAPI 启动时自动执行 start_email_scheduler()
@app.on_event("startup")
def start_email_scheduler():
    # - `threading.Thread()`：创建一个新线程      - `target=start_scheduler`：这个线程要执行的函数是 `start_scheduler`      - `daemon=True`：后台线程，不阻塞主程序，主程序退出时自动结束     `.start()`：启动线程
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
