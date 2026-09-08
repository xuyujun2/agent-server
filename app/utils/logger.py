import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - 【%(name)s】 - %(levelname)s  - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
