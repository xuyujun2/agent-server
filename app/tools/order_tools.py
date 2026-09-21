import asyncio

from langchain.tools import tool
from pydantic import BaseModel, Field

from app.utils.logger import logger
from app.services.order_service import (
    get_order_by_no,
    get_orders_by_user,
    create_return_request
)


class QueryOrderInput(BaseModel):
    order_no: str = Field(description="订单号，格式如 ORD20260805007")


class QueryMyOrdersInput(BaseModel):
    pass


class ApplyReturnInput(BaseModel):
    order_no: str = Field(description="订单号，格式如 ORD20260805007")
    reason: str = Field(description="退货原因，从用户原话中提取，不能自行猜测")


def build_order_tools(user_id: str):
    """将当前请求的用户ID绑定到订单工具，不交给模型填写。"""

    @tool(args_schema=QueryOrderInput)
    async def query_order(order_no: str) -> str:
        """根据订单号查询当前用户的订单信息。"""
        logger.info("[工具开始] query_order 查订单，订单号=%s", order_no)
        try:
            order = await asyncio.to_thread(get_order_by_no, order_no, user_id)
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
    async def query_my_orders() -> str:
        """查询当前用户的所有订单列表。"""
        logger.info("[工具开始] query_my_orders 查用户订单，用户ID=%s", user_id)
        try:
            orders = await asyncio.to_thread(get_orders_by_user, user_id)
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
    async def apply_return(order_no: str, reason: str) -> str:
        """为当前用户提交退货申请，需要订单号和退货原因。"""
        # 不打印退货原因全文，避免把用户填写的私人信息记入日志。
        logger.info("[工具开始] apply_return 申请退货，订单号=%s，用户ID=%s", order_no, user_id)
        try:
            result = await asyncio.to_thread(create_return_request, order_no, user_id, reason)
            answer = result["msg"]
            logger.info(
                "[工具结束] apply_return，订单号=%s，用户ID=%s，结果=%s",
                order_no, user_id, "提交成功" if result.get("success") else "未提交成功",
            )
            return answer
        except Exception:
            logger.exception("[工具报错] apply_return，订单号=%s，用户ID=%s", order_no, user_id)
            raise

    return [query_order, query_my_orders, apply_return]
