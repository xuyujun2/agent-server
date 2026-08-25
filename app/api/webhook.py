from fastapi import APIRouter, HTTPException
from app.models.schemas import WebhookUnpaidRequest, WebhookPaidRequest, WebhookShippedRequest
from app.database.db import execute_query, execute_update
from app.utils.logger import logger

router = APIRouter(prefix="/webhook", tags=["回调"])

@router.post("/unpaid")
def handle_unpaid(request: WebhookUnpaidRequest):
    """
    未支付回调
    支付平台调这个接口通知你：订单尚未支付
    """
    logger.info(f"收到未支付回调: {request.order_no}")

    # 先查订单是否存在
    exist = execute_query("SELECT * FROM orders WHERE order_no=%s", (request.order_no,))
    if not exist:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 项目的订单状态使用“待支付”表示尚未支付
    execute_update("UPDATE orders SET status='待支付' WHERE order_no=%s", (request.order_no,))
    return {"code": 0, "msg": "订单状态已更新为待支付"}


@router.post("/paid")
def handle_paid(request: WebhookPaidRequest):
    """
    支付完成回调
    支付平台调这个接口通知你：钱到了
    """
    logger.info(f"收到支付回调: {request.order_no}, 金额: {request.paid_amount}")
    
    # 先查订单是否存在
    exist = execute_query("SELECT * FROM orders WHERE order_no=%s", (request.order_no,))
    if not exist:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 再更新订单状态为"已支付"
    execute_update("UPDATE orders SET status='已支付' WHERE order_no=%s", (request.order_no,))
    return {"code": 0, "msg": "订单状态更新成功"}


@router.post("/shipped")
def handle_shipped(request: WebhookShippedRequest):
    """
    发货完成回调
    物流系统调这个接口通知你：货已发出
    """
    logger.info(f"收到发货回调: {request.order_no}, 快递: {request.logistics_company}")
    
    # 先查订单是否存在
    exist = execute_query("SELECT * FROM orders WHERE order_no=%s", (request.order_no,))
    if not exist:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 再更新订单状态为"已发货"
    execute_update("UPDATE orders SET status='已发货' WHERE order_no=%s", (request.order_no,))
    return {"code": 0, "msg": "发货状态更新成功"}


@router.post("/delivered")
def handle_delivered(request: WebhookShippedRequest):
    """
    签收回调
    物流系统调这个接口通知你：用户已签收
    """
    logger.info(f"收到签收回调: {request.order_no}")
    
    # 先查订单是否存在
    exist = execute_query("SELECT * FROM orders WHERE order_no=%s", (request.order_no,))
    if not exist:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 再更新订单状态为"已签收"
    execute_update("UPDATE orders SET status='已签收' WHERE order_no=%s", (request.order_no,))
    return {"code": 0, "msg": "签收状态更新成功"}
