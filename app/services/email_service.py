import os
import pickle
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from app.config import Config

# ====== Gmail API 认证 ======

# 2个 Gmail API      权限范围。告诉Google：“这个程序需要读取邮件和发送邮件两个权限。”
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.send']

# 搞一个登陆凭证，谷歌给程序授权，授读邮件、发邮件的权限
def get_gmail_service():
    """获取Gmail API服务对象"""
    creds = None
    # 检查本地是否存在 token.pickle 文件    token.pickleL 登录凭证文件
    if os.path.exists('token.pickle'):
        # 'rb'：read binary，读取二进制文件
        with open('token.pickle', 'rb') as token:
            # pickle 是 Python 内置的序列化模块，用于从文件恢复对象     pickle.load(token)：加载里面的登录凭证文件里面的内容(登录凭证对象)，避免每次都要重新登录。
            creds = pickle.load(token)
    
    # valid: 是否有效    expired: 过期   refresh_token: 有刷新令牌
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 刷新请求，获取新的登录凭证 creds
            creds.refresh(Request())
        else:
            # 用Google提供的配置文件创建授权流程    SCOPES：权限范围列表，告诉 Google 这个程序需要哪些权限
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # creds: 凭证对象   flow：授权流程对象     在本地开一个临时网页，让用户手动登录授权，port=0自动分配端口      授什么权：授权 Gmail API，Google给程序授权
            creds = flow.run_local_server(port=0)
        # 以二进制写入模式打开文件。没有就新创建一个
        with open('token.pickle', 'wb') as token:
            # 把 creds（凭证对象）写入 token.pickle 文件
            pickle.dump(creds, token)
    
    # 创建 Gmail API 客户端对象，后续用这个对象调用 Gmail API（如读邮件、发邮件）。`'gmail'` 是服务名，`'v1'` 是版本号，`credentials=creds` 传入凭证用于认证。
    return build('gmail', 'v1', credentials=creds)

# ====== 读取邮件 ======

def get_unread_emails(service, max_results=5):
    """获取未读邮件"""
    # 调用 Gmail API 读取当前用户的未读邮件列表：   results 是接口返回的完整响应对象，包含 messages 字段（邮件列表）和其他元数据。
    # - `service.users()`：进入用户维度      - `service.users().messages()`：进入消息维度    - `.list()` 是 `messages` 对象的方法，用于查询邮件列表
    # - `userId='me'`：当前授权用户    - `q='is:unread'`：只查未读邮件    - `maxResults=max_results`：最多返回几条    - `.execute()`：发送请求，执行操作，返回结果
    # 一个程序可以管理多个 Gmail 账户（比如同时登录工作邮箱和个人邮箱），userId='me' 指定操作当前登录(授权)的那个邮箱
    results = service.users().messages().list(
        userId='me', 
        q='is:unread', 
        maxResults=max_results
    ).execute()
    
    emails = []
    for msg in results.get('messages', []):
        # 获取某封邮件的完整详情（包含正文、发件人、主题等）。  format='full'：返回完整内容（含正文）   .execute()：执行请求返回数据
        msg_data = service.users().messages().get(
            userId='me', 
            id=msg['id'],
            format='full'
        ).execute()
        
        # 解析邮件头
        # 从邮件数据里取邮件头列表（含主题、发件人等）    payload：是整个邮件内容
        headers = msg_data['payload']['headers']
        # next(...)：从生成器中取第一个匹配的值，没有则返回默认值    h['value'] 是取值的意思
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '无主题')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '未知发件人')
        
        # 解析正文
        body = ''
        # parts：正文列表 [纯文本,HTML,附件]      part: 正文，就是列表里的纯文本、HTML、附件
        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    # Base64 解码
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        else:
            # 处理没有 parts 的简单正文。比如正文只有纯文本（mimeType == 'text/plain'）
            if msg_data['payload']['mimeType'] == 'text/plain':
                data = msg_data['payload']['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        emails.append({
            'id': msg['id'],
            'sender': sender,
            'subject': subject,
            'body': body[:500]  # 截断，防止太长
        })
    
    return emails

# ====== 生成回复 ======

def generate_reply(sender, subject, body):
    """用AI生成回复草稿"""
    llm = ChatOpenAI(
        model=Config.MODEL_NAME,
        api_key=Config.OPENAI_API_KEY,
        base_url=Config.BASE_URL
    )
    
    prompt = PromptTemplate.from_template("""
你是一个专业的邮件助手。根据以下邮件内容，生成一封回复草稿。

发件人：{sender}
主题：{subject}
正文：{body}

要求：
1. 语气礼貌、专业
2. 先确认收到，再回应内容
3. 如果信息不足，礼貌地请求补充
4. 200字以内
5. 只输出回复内容

回复草稿：
""")
    
    chain = prompt | llm
    response = chain.invoke({
        "sender": sender,
        "subject": subject,
        "body": body
    })
    return response.content

# ====== 发送邮件 ======

def send_email(service, to, subject, body):
    """发送邮件"""
    message = EmailMessage()

    # 设置收件人
    message['To'] = to

    # 设置主题
    message['Subject'] = f"回复：{subject}"

    # 设置 UTF-8 纯文本正文
    message.set_content(body, charset='utf-8')

    # Gmail API 要求整封邮件转换为 Base64 URL-safe 字符串
    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode('utf-8')
    
    service.users().messages().send(
        userId='me',
        body={'raw': encoded_message}
    ).execute()

# ====== 移除未读标记 ======

def mark_email_as_read(service, msg_id):
    """移除原邮件的未读标记，防止定时任务重复处理"""
    # 需要审核的邮件插入数据库时，把邮件id插入了表字段 msg_id
    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
