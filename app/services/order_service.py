from app.database.db import execute_query, execute_update
from app.utils.logger import logger

def get_order_by_no(order_no: str, user_id: str = None):
    """查询订单"""
    sql = "SELECT * FROM orders WHERE order_no = %s"
    params = [order_no]
    if user_id:
        sql += " AND user_id = %s"
        params.append(user_id)
    result = execute_query(sql, params)
    return result[0] if result else None

def get_orders_by_user(user_id: str):
    """查询用户所有订单"""
    return execute_query(
        "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    )

def check_return_eligible(order_no: str) -> tuple:
    """
    检查是否满足退货条件
    返回：(是否可退, 原因)
    """
    order = get_order_by_no(order_no)
    if not order:
        return False, "订单不存在"
    
    status = order.get('status', '')
    
    # 规则：只有已发货、已签收、已完成状态才能退货
    if status not in ['已发货', '已签收', '已完成']:
        return False, f"当前订单状态为'{status}'，不可退货，请等待发货后再申请"
    
    # TODO: 可以再加15天时效判断
    return True, "符合退货条件"

def create_return_request(order_no: str, user_id: str, reason: str):
    """创建退货申请"""
    # 再次检查是否可退
    eligible, msg = check_return_eligible(order_no)
    if not eligible:
        return {"success": False, "msg": msg}
    
    # 检查是否已经申请过退货
    existing = execute_query(
        "SELECT * FROM returns WHERE order_no = %s AND status IN ('待审核', '已通过')",
        (order_no,)
    )
    if existing:
        return {"success": False, "msg": "该订单已申请过退货，请勿重复提交"}
    
    # 插入退货申请
    sql = """
        INSERT INTO returns (order_no, user_id, reason, status)
        VALUES (%s, %s, %s, '待审核')
    """
    execute_update(sql, (order_no, user_id, reason))
    logger.info(f"退货申请创建成功: {order_no}, 用户: {user_id}")
    
    return {"success": True, "msg": "退货申请已提交，等待客服审核"}

def approve_return(return_id: int):
    """审核通过退货（后台调用）"""
    # 更新状态
    execute_update(
        "UPDATE returns SET status = '已通过' WHERE id = %s",
        (return_id,)
    )
    # 这里可以触发物流API
    return get_return_by_id(return_id)

def get_return_by_id(return_id: int):
    """查询退货单"""
    result = execute_query("SELECT * FROM returns WHERE id = %s", (return_id,))
    return result[0] if result else None
