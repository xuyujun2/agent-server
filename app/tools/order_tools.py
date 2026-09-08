from langchain.tools import tool
from pydantic import BaseModel, Field

from app.utils.logger import logger
from app.services.order_service import (
    get_order_by_no,
    get_orders_by_user,
    check_return_eligible,
    create_return_request
)


class QueryOrderInput(BaseModel):
    order_no: str = Field(description="订单号，格式如 ORD20260805007")


class QueryMyOrdersInput(BaseModel):
    user_id: str = Field(description="用户ID，格式如 user_006，从用户提供的信息中提取")


class ApplyReturnInput(BaseModel):
    order_no: str = Field(description="订单号，格式如 ORD20260805007")
    reason: str = Field(description="退货原因，从用户原话中提取，不能自行猜测")
    user_id: str = Field(description="用户ID，格式如 user_006，从用户提供的信息中提取")


@tool(args_schema=QueryOrderInput)
def query_order(order_no: str) -> str:
    """
    根据订单号查询订单信息。
    用户提供订单号时调用。
    """
    logger.info("[工具开始] query_order 查订单，订单号=%s", order_no)
    try:
        order = get_order_by_no(order_no)
        if not order:
            logger.info("[工具结束] query_order，订单号=%s，未找到订单", order_no)
            return "未找到该订单，请确认订单号是否正确"

        answer = f"""订单号：{order['order_no']}
商品：{order['product_name']}
价格：{order['product_price']}元
状态：{order['status']}"""
        logger.info("[工具结束] query_order，订单号=%s，找到订单", order_no)
        return answer
    except Exception:
        logger.exception("[工具报错] query_order，订单号=%s", order_no)
        raise

@tool(args_schema=QueryMyOrdersInput)
def query_my_orders(user_id: str) -> str:
    """
    查询用户的所有订单列表。
    用户问"我的订单"、"查我买的东西"时调用。
    """
    logger.info("[工具开始] query_my_orders 查用户订单，用户ID=%s", user_id)
    try:
        orders = get_orders_by_user(user_id)
        if not orders:
            logger.info("[工具结束] query_my_orders，用户ID=%s，未找到订单", user_id)
            return "您暂无订单"

        lines = ["您的订单列表："]
        for o in orders:
            lines.append(f"- {o['order_no']} | {o['product_name']} | {o['status']}")
        answer = "\n".join(lines)
        logger.info("[工具结束] query_my_orders，用户ID=%s，找到%s条订单", user_id, len(orders))
        return answer
    except Exception:
        logger.exception("[工具报错] query_my_orders，用户ID=%s", user_id)
        raise

@tool(args_schema=ApplyReturnInput)
def apply_return(order_no: str, reason: str, user_id: str) -> str:
    """
    提交退货申请。
    用户明确说"要退货"、"申请退货"时调用。
    需要提供订单号和退货原因。
    """
    # 不打印退货原因全文，避免把用户填写的私人信息记入日志。
    logger.info("[工具开始] apply_return 申请退货，订单号=%s，用户ID=%s", order_no, user_id)
    try:
        result = create_return_request(order_no, user_id, reason)
        answer = result["msg"]
        logger.info(
            "[工具结束] apply_return，订单号=%s，用户ID=%s，结果=%s",
            order_no, user_id, "提交成功" if result.get("success") else "未提交成功",
        )
        return answer
    except Exception:
        logger.exception("[工具报错] apply_return，订单号=%s，用户ID=%s", order_no, user_id)
        raise
