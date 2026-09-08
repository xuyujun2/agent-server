import requests
import time
import hmac
import hashlib
import base64

def send_dingtalk_alert(content: str):
    token = "4a20ee85d5d794f607db009fc064a3997c45698d64b3d51502080e3be40af075"
    secret = "SEC6dcaa939cac24981028ee1a639b285bb79a21ea395ea6ccaf26d950f1c52f4c6"

    timestamp = str(round(time.time() * 1000))
    sign_str = timestamp + "\n" + secret
    sign = base64.b64encode(hmac.new(secret.encode(), sign_str.encode(), hashlib.sha256).digest()).decode()

    url = f"https://oapi.dingtalk.com/robot/send?access_token={token}&timestamp={timestamp}&sign={sign}"

    requests.post(url, json={
        "msgtype": "text",
        "text": {"content": f"客服接口告警：{content}"}
    }, timeout=5)


