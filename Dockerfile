FROM python:3.11-slim

WORKDIR /app

# 安装中文字体，供批改图片显示中文批改说明。
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt -i https://pypi.org/simple

COPY . .

# app.main:app => 去app文件夹，找到main.py文件里的变量app，也就是 FastAPI()
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]  
