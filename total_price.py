from decimal import Decimal
from typing import Iterable, Mapping, Union


Number = Union[int, float, Decimal, str]


def calculate_total_price(
    items: Iterable[Mapping[str, Number]],
    discount: Number = Decimal("0"),
    tax_rate: Number = Decimal("0"),
) -> Decimal:
    """计算商品总价，并依次应用折扣和税率。

    每件商品必须包含 ``price`` 和 ``quantity``。折扣和税率均使用
    0 到 1 之间的小数表示，例如 0.1 表示 10%。返回值保留两位小数。
    """
    discount_value = Decimal(str(discount))
    tax_rate_value = Decimal(str(tax_rate))

    if not Decimal("0") <= discount_value <= Decimal("1"):
        raise ValueError("discount must be between 0 and 1")
    if tax_rate_value < Decimal("0"):
        raise ValueError("tax_rate must be non-negative")

    subtotal = Decimal("0")
    for item in items:
        price = Decimal(str(item["price"]))
        quantity = Decimal(str(item["quantity"]))
        if price < Decimal("0"):
            raise ValueError("price must be non-negative")
        if quantity < Decimal("0"):
            raise ValueError("quantity must be non-negative")
        subtotal += price * quantity

    total = subtotal * (Decimal("1") - discount_value)
    total *= Decimal("1") + tax_rate_value
    return total.quantize(Decimal("0.01"))
