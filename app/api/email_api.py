from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.database.db import execute_query, execute_update
from app.services.email_service import get_gmail_service, send_email, mark_email_as_read

router = APIRouter(prefix="/email", tags=["邮件"])

class SendRequest(BaseModel):
    ids: List[int]

@router.get("/drafts")
def get_drafts():
    rows = execute_query("SELECT * FROM email_drafts ORDER BY created_at DESC")
    return {"code": 0, "data": rows}

@router.post("/send")
def send_drafts(req: SendRequest):
    if not req.ids:
        return {"code": 1, "msg": "未选择任何邮件"}
    
    service = get_gmail_service()
    sent_count = 0
    for draft_id in req.ids:
        row = execute_query("SELECT * FROM email_drafts WHERE id=%s", (draft_id,))
        if not row:
            continue
        draft = row[0]
        try:
            send_email(service, draft['sender'], draft['subject'], draft['reply'])
            mark_email_as_read(service, draft['msg_id'])
            execute_update("DELETE FROM email_drafts WHERE id=%s", (draft_id,))
            sent_count += 1
        except Exception:
            continue
    return {"code": 0, "msg": f"已发送 {sent_count} 封邮件"}
