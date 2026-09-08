import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 数据库
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
    DB_NAME = os.getenv("DB_NAME", "customer_service")

    # Redis（本地默认连接本机；Docker 部署时通过环境变量改为 redis://redis:6379/0）
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "你的key")
    # MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")  # deepseek的 MODEL_NAME，先测试用，后面要改成 OpenAI Platform 的 MODEL_NAME
    BASE_URL = os.getenv("BASE_URL", "https://api.deepseek.com/v1")  # deepseek的 API key，先测试用，后面要改成 OpenAI Platform 的 API key

    # 视觉识别模型（只负责把答案和试卷图片识别成文字）
    VISION_API_KEY = os.getenv("VISION_API_KEY", "")
    VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", "gpt-5")
    VISION_BASE_URL = os.getenv("VISION_BASE_URL", "https://api.openai.com/v1")
    
    # 物流API（快递鸟）
    KDNIAO_API_KEY = os.getenv("KDNIAO_API_KEY", "")
    KDNIAO_SECRET = os.getenv("KDNIAO_SECRET", "")
    
    # 服务
    MAX_RETURN_ROUNDS = int(os.getenv("MAX_RETURN_ROUNDS", "3"))

    # Gmail
    GMAIL_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "token.pickle")
    ALLOWED_SENDERS = os.getenv("ALLOWED_SENDERS", "@gmail.com,@qq.com,@company.com").split(",")
