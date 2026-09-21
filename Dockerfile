FROM python:3.11-slim

WORKDIR /app

# 安装中文字体，供批改图片显示中文批改说明。
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk && rm -rf /var/lib/apt/lists/*

# 因为PyTorch包很大（几百MB），从PyPI默认源下载慢且容易失败。单独指定官方CPU源、加大超时和重试，能稳定装下来。而且分开写能利用Docker缓存——PyTorch这层不变时，重新构建镜像不会重复下载。
# 第一次慢，正常，Docker有缓存机制：后面只要这行命令没变，就会用缓存
RUN pip install \
    --timeout 1000 \
    --retries 5 \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .

RUN pip install \
    --timeout 1000 \
    --retries 5 \
    -r requirements.txt \
    -i https://pypi.org/simple

COPY . .

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
