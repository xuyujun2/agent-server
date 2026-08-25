from decimal import Decimal
from typing import Iterable, Mapping, Union


Number = Union[int, float, Decimal]


def calculate_total(items: Iterable[Mapping[str, Number]]) -> Decimal:
    """计算商品总价。

    每件商品需包含 ``price``（单价）和 ``quantity``（数量）。
    返回 Decimal，以避免常见的浮点金额精度问题。
    """
    total = Decimal("0")

    for item in items:
        if "price" not in item or "quantity" not in item:
            raise KeyError("每件商品必须包含 price 和 quantity")

        price = Decimal(str(item["price"]))
        quantity = Decimal(str(item["quantity"]))

        if price < 0:
            raise ValueError("商品单价不能为负数")
        if quantity < 0:
            raise ValueError("商品数量不能为负数")

        total += price * quantity

    return total.quantize(Decimal("0.01"))
