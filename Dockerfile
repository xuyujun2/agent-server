FROM python:3.11-slim

WORKDIR /app

# 安装中文字体，供批改图片显示中文批改说明。
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt -i https://pypi.org/simple

COPY . .

# 启动 uvicorn 服务器，把你的 FastAPI 接口跑起来   app.main:app => 去app文件夹，找到main.py文件里的变量app，也就是 FastAPI()
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]  






# COPY . .   第一个点是项目根目录，第二个点是创建的app目录    把项目根目录里所有内容复制进app目录
# 容器内 /
# └── app/                        # WORKDIR 建的
#     ├── app/                    # 你项目里的 app 文件夹
#     │   ├── main.py
#     │   ├── api/...
#     │   └── ...
#     ├── code_mcp_server.py
#     ├── requirements.txt
#     └── Dockerfile
