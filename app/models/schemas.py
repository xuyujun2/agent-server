from pydantic import BaseModel
from typing import Optional

class Order(BaseModel):
    order_no: str
    user_id: str
    product_name: str
    product_price: float
    status: str

class ReturnRequest(BaseModel):
    order_no: str
    user_id: str
    reason: str

class WebhookUnpaidRequest(BaseModel):
    order_no: str

class WebhookPaidRequest(BaseModel):
    order_no: str
    transaction_id: str
    paid_amount: float

class WebhookShippedRequest(BaseModel):
    order_no: str
    logistics_company: str
    tracking_no: str

class AskRequest(BaseModel):
    user_id: str
    question: str
