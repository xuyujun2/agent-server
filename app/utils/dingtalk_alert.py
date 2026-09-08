import requests
import time
import hmac
import hashlib
import base64`r`nimport os`r`n

def send_dingtalk_alert(content: str):
    token = os.getenv("DINGTALK_TOKEN")
    secret = os.getenv("DINGTALK_SECRET")

    timestamp = str(round(time.time() * 1000))
    sign_str = timestamp + "\n" + secret
    sign = base64.b64encode(hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).digest()).decode()

    url = f"https://oapi.dingtalk.com/robot/send?access_token={token}&timestamp={timestamp}&sign={sign}"

    requests.post(url, json={
        "msgtype": "text",
        "text": {"content": f"客服接口告警：{content}"}
    }, timeout=5)

