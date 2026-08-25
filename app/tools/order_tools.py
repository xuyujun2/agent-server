from langchain.tools import tool
from app.services.order_service import (
    get_order_by_no,
    get_orders_by_user,
    check_return_eligible,
    create_return_request
)

@tool
def query_order(order_no: str) -> str:
    """
    根据订单号查询订单信息。
    用户提供订单号时调用。
    """
    order = get_order_by_no(order_no)
    if not order:
        return "未找到该订单，请确认订单号是否正确"
    
    return f"""订单号：{order['order_no']}
商品：{order['product_name']}
价格：{order['product_price']}元
状态：{order['status']}"""

@tool
def query_my_orders(user_id: str) -> str:
    """
    查询用户的所有订单列表。
    用户问"我的订单"、"查我买的东西"时调用。
    """
    orders = get_orders_by_user(user_id)
    if not orders:
        return "您暂无订单"
    
    lines = ["您的订单列表："]
    for o in orders:
        lines.append(f"- {o['order_no']} | {o['product_name']} | {o['status']}")
    return "\n".join(lines)

@tool
def apply_return(order_no: str, reason: str, user_id: str) -> str:
    """
    提交退货申请。
    用户明确说"要退货"、"申请退货"时调用。
    需要提供订单号和退货原因。
    """
    result = create_return_request(order_no, user_id, reason)
    return result["msg"]
