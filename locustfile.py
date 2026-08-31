"""智能客服接口压测脚本。

启动方式：
1. 先启动 FastAPI 服务。 就是启动本地服务。
2. 执行：locust -f locustfile.py --host=http://localhost:8000
3. 浏览器打开：http://localhost:8089

注意：未命中缓存的请求会真实调用大模型，可能产生 API 费用。

怎么模拟高并发：
你指定并发用户数（比如100），它会创建100个虚拟用户，每个用户按你自己的设定循环执行任务（气泡请求占80%、Agent请求占20%）。100个用户同时持续发请求，这就是高并发模拟。

不是100个用户同时点一次，而是100个用户持续不断地发请求。 这样你的服务器会持续收到请求，你能看到QPS、P95延迟、错误率。

你打开 http://localhost:8089 的网页界面，填并发用户数，点开始，就能看到实时数据。
"""

import uuid

from locust import HttpUser, between, task


class CustomerServiceUser(HttpUser):
    """模拟访问智能客服的用户。"""

    # 每个虚拟用户完成一次请求后，等待 1～2 秒再发送下一次请求。
    wait_time = between(1, 2)

    def on_start(self):
        """每个虚拟用户启动时生成独立的 user_id。"""
        self.user_id = f"load_test_{uuid.uuid4().hex}"

    # task(8) 代表 80% 的用户模拟这个接口
    @task(8)
    def ask_fixed_faq(self):
        """模拟点击固定问题气泡，占总请求的大约 80%。"""

        with self.client.post(
            "/agent/ask",
            json={
                "user_id": self.user_id,
                "question": "退款多久到账",
            },
            # 在 Locust 报表中单独统计固定 FAQ 请求。
            name="/agent/ask [固定FAQ]",
            catch_response=True,
        ) as response:
            # as response：拿到响应对象，传给 _check_response 做内容校验
            self._check_response(response)

    @task(2)
    def ask_agent(self):
        """模拟缓存未命中并调用 Agent，占总请求的大约 20%。"""

        with self.client.post(
            "/agent/ask",
            json={
                "user_id": self.user_id,
                "question": "请介绍一下你们的售后处理流程",
            },
            # 在 Locust 报表中单独统计 Agent 请求。
            name="/agent/ask [Agent]",
            catch_response=True,
        ) as response:
            self._check_response(response)

    @staticmethod
    def _check_response(response):
        """检查接口是否真正返回了有效答案。"""

        if response.status_code != 200:
            response.failure(f"HTTP状态码：{response.status_code}")
            return

        try:
            body = response.json()
        except ValueError:
            response.failure("响应不是合法JSON")
            return

        answer = body.get("data", {}).get("answer")

        if not answer:
            response.failure("响应中没有answer字段")
            return

        response.success()
