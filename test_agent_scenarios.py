"""通过现有接口测试智能客服。

先启动 myagent，再运行：
# 跑所有用例
docker exec -e PYTHONIOENCODING=utf-8 myagent python test_agent_scenarios.py
# 只跑前两个用例
docker exec -e PYTHONIOENCODING=utf-8 myagent python test_agent_scenarios.py --limit 2
"""

import argparse
import json
from urllib.request import Request, urlopen


API_URL = "http://127.0.0.1:8000/agent/ask"


# questions 是用户问题；有两句话时，表示连续对话。
# expected_words 是正确回答里必须出现的文字。
TEST_CASES = [
    {
        "name": "查询已支付订单",
        "user_id": "user_006",
        "questions": ["帮我查订单 ORD20260805006"],
        "expected_words": ["iPhone 15 Pro Max", "已支付"],
    },
    {
        "name": "查询已发货订单",
        "user_id": "user_006",
        "questions": ["帮我查订单 ORD20260805007 的状态"],
        "expected_words": ["AirPods Pro 2", "已发货"],
    },
    {
        "name": "换一种说法查订单",
        "user_id": "user_006",
        "questions": ["ORD20260805007 发货了吗？"],
        "expected_words": ["AirPods Pro 2", "已发货"],
    },
    {
        "name": "查询已签收订单",
        "user_id": "user_006",
        "questions": ["ORD20260805008 是什么状态？"],
        "expected_words": ["MacBook Pro 14", "已签收"],
    },

    {
        "name": "查询已完成订单",
        "user_id": "user_007",
        "questions": ["查询 ORD20260805009"],
        "expected_words": ["iPad Air", "已完成"],
    },
    {
        "name": "查询待支付订单",
        "user_id": "user_007",
        "questions": ["订单 ORD202608050010 支付了吗？"],
        "expected_words": ["Apple Watch", "待支付"],
    },
    {
        "name": "同时提供订单号和用户ID",
        "user_id": "user_006",
        "questions": ["订单号 ORD20260805007，用户ID是 user_006，帮我查状态"],
        "expected_words": ["AirPods Pro 2", "已发货"],
    },
    {
        "name": "查询不存在的订单",
        "user_id": "user_006",
        "questions": ["查一下订单 ORD99999999999"],
        "expected_words": ["未找到"],
    },
    {
        "name": "查询user_006的全部订单",
        "user_id": "user_006",
        "questions": ["查询 user_006 的全部订单"],
        "expected_words": ["ORD20260805006", "ORD20260805007", "ORD20260805008"],
    },
    {
        "name": "查询user_007的全部订单",
        "user_id": "user_007",
        "questions": ["user_007 买过什么？"],
        "expected_words": ["ORD20260805009", "ORD202608050010"],
    },
    {
        "name": "查询不存在的用户",
        "user_id": "user_999",
        "questions": ["查询 user_999 的全部订单"],
        "expected_words": ["暂无订单"],
    },
    {
        "name": "没有订单号时先追问",
        "user_id": "user_006",
        "questions": ["帮我查订单状态"],
        "expected_words": ["订单号"],
    },
    {
        "name": "没有用户ID时先追问",
        "user_id": "user_006",
        "questions": ["查询我的全部订单"],
        "expected_words": ["用户ID"],
    },
    {
        "name": "多轮对话中补充订单号",
        "user_id": "user_006",
        "questions": ["帮我查订单状态", "ORD20260805007"],
        "expected_words": ["AirPods Pro 2", "已发货"],
    },
]


def ask_customer(user_id, question):
    """调用项目现有的 /agent/ask 接口。"""
    body = json.dumps({
        "user_id": user_id,
        "question": question,
    }).encode("utf-8")

    request = Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["data"]["answer"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(TEST_CASES))
    args = parser.parse_args()

    passed = 0
    selected_cases = TEST_CASES[:args.limit]

    for index, case in enumerate(selected_cases, start=1):
        user_id = case["user_id"]

        try:
            # 同一条用例里的多句话使用同一个用户ID，用来测试聊天记忆。
            for question in case["questions"]:
                answer = ask_customer(user_id, question)
            missing_words = [
                word for word in case["expected_words"]
                if word not in answer
            ]

            if not missing_words:
                passed += 1
                print(f"[{index}] 通过：{case['name']}")
            else:
                print(f"[{index}] 失败：{case['name']}")
                print(f"    回答里缺少：{missing_words}")
                print(f"    实际回答：{answer}")
        except Exception as error:
            print(f"[{index}] 报错：{case['name']}")
            print(f"    {error}")

    print(f"\n测试完成：通过 {passed}/{len(selected_cases)}")


if __name__ == "__main__":
    main()
