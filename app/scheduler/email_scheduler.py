import schedule
import time
from app.services.email_service import get_gmail_service, get_unread_emails, generate_reply, send_email, mark_email_as_read
from app.database.db import execute_query, execute_update
from app.config import Config

# 自动发送关键词（包含这些关键词的邮件直接自动回复）
AUTO_KEYWORDS = ["系统通知", "验证码", "noreply", "自动", "订阅"]

def job():
    try:
        service = get_gmail_service()
        emails = get_unread_emails(service, max_results=10)
        
        for email in emails:
            # 1. 检查是否已处理
            existing = execute_query("SELECT id FROM email_drafts WHERE msg_id=%s", (email['id'],))
            if existing:
                continue
            
            # 2. 检查白名单   检查发件人是否在允许列表中   any()函数表示有任意一个符合条件，就返回true    any()括号里规定先执行后面，前面的是条件   not: 对any()取反
            if not any(domain in email['sender'] for domain in Config.ALLOWED_SENDERS):
                # continue 跳过的是 for email in emails 这个循环的当前这一次   继续下一封邮件
                continue
            
            # 3. 判断是自动发送还是人工审核
            is_auto = any(keyword in email['subject'] for keyword in AUTO_KEYWORDS)
            
            if is_auto:
                # 自动发送类：直接回复
                reply = generate_reply(email['sender'], email['subject'], email['body'])
                send_email(service, email['sender'], email['subject'], reply)
                mark_email_as_read(service, email['id'])
            else:
                # 人工审核类：存入数据库，等待Web端勾选发送
                reply = generate_reply(email['sender'], email['subject'], email['body'])
                execute_update(
                    "INSERT INTO email_drafts (msg_id, sender, subject, body, reply) VALUES (%s, %s, %s, %s, %s)",
                    (email['id'], email['sender'], email['subject'], email['body'], reply)
                )
                
    except Exception:
        pass

def start_scheduler():
    schedule.every(2).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
