import base64
import os

import docker
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate


# 读取项目根目录下的 .env 配置
load_dotenv()

# 配置模型（使用 DeepSeek）
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.deepseek.com/v1",
)


def _clean_code(code: str) -> str:
    """移除模型可能返回的 Markdown 代码块标记。"""
    if "```python" in code:
        code = code.split("```python", 1)[1].split("```", 1)[0]
    elif "```" in code:
        code = code.split("```", 1)[1].split("```", 1)[0]
    return code.strip()


# 检查业务代码
def run_code(code: str) -> str:
    """在独立容器中执行生成的业务代码。"""
    # 把业务代码 code 存进变量 encoded_code
    encoded_code = base64.b64encode(code.encode("utf-8")).decode("ascii")

    # os.environ['SANDBOX_CODE'] 获取环境变量，也就是获取到了业务代码
    # exec()：执行 Python 代码字符串，就等于是运行代码，看代码有没有报错    compile(code, '<generated_code>', 'exec')：把代码字符串编译成可执行代码对象
    command = [
        "python",
        "-c",
        (
            "import base64, os; "
            "code = base64.b64decode(os.environ['SANDBOX_CODE']).decode('utf-8'); "
            "exec(compile(code, '<generated_code>', 'exec'))"
        ),
    ]

    container = None
    try:
        # docker.from_env()：从当前环境读取 Docker 配置并创建一个 Docker 客户端对象 client
        client = docker.from_env()
        # client.containers.run：调用 Docker 客户端创建并启动一个独立于当前进程的临时容器，也就是沙箱
        container = client.containers.run(
            image="python:3.11-slim",
            command=command,  # command=command：容器启动后执行的命令
            environment={"SANDBOX_CODE": encoded_code},  # 把业务代码存进沙箱的环境变量 SANDBOX_CODE
            mem_limit="128m",                    # 最多使用 128MB 内存
            nano_cpus=500_000_000,                # 最多使用 0.5 个 CPU 核心
            pids_limit=64,                        # 最多创建 64 个进程
            network_disabled=True,                # 禁止访问网络
            read_only=True,                       # 根文件系统设为只读
            cap_drop=["ALL"],                     # 删除 Linux 额外权限
            security_opt=["no-new-privileges"],   # 禁止进程提升权限
            detach=True,                          # 后台启动，便于等待和强制终止
        )

        try:
            # 最多等待 60 秒，避免生成的代码永久占用资源。
            result = container.wait(timeout=60)
        except Exception:
            container.kill()
            return "执行超时（10秒）"

        # 打印沙箱运行的结果，就打印这两个东西 stdout=True, stderr=True 标准输出和标准错误
        logs = container.logs(stdout=True, stderr=True).decode(
            "utf-8",
            errors="replace",
        )

        if result.get("StatusCode") == 0:
            return f"执行成功：\n{logs or '无输出'}"

        return f"执行失败：\n{logs}"
    except Exception as error:
        return f"执行异常：{error}"
    finally:
        # 无论成功、失败或超时，最终都删除一次性沙箱容器。
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass


# 检查测试代码
def run_tests(function_code: str, test_code: str) -> str:
    """在独立容器中保存业务代码和测试代码，并通过 pytest 执行测试。"""
    # 分别编码业务代码和测试代码，通过环境变量传入沙箱容器。
    encoded_function = base64.b64encode(function_code.encode("utf-8")).decode("ascii")
    encoded_test = base64.b64encode(test_code.encode("utf-8")).decode("ascii")

    # 在沙箱的临时目录中创建 target.py 和 test_target.py，再运行 pytest。
    # pathlib.Path('/tmp/code_tests'): 创建一个路径对象，表示 /tmp/code_tests 这个位置，但还没执行
    # workdir.mkdir(parents=True, exist_ok=True)：执行创建动作
    # workdir / 'target.py'：拼接路径，相当于 /tmp/code_tests/target.py
    # os.chdir(workdir): 切换当前工作目录到 /tmp/code_tests
    # 用pest库运行 test_target.py，main() 是 pytest 库的入口函数，-q 表示简洁输出，sys.exit()是执行完，退出 
    runner = (
        "import base64, os, pathlib, pytest, sys; "
        "workdir = pathlib.Path('/tmp/code_tests'); "
        "workdir.mkdir(parents=True, exist_ok=True); "
        "(workdir / 'target.py').write_bytes(base64.b64decode(os.environ['FUNCTION_CODE'])); "
        "(workdir / 'test_target.py').write_bytes(base64.b64decode(os.environ['TEST_CODE'])); "
        "os.chdir(workdir); "
        "sys.exit(pytest.main(['-q', 'test_target.py']))"
    )

    container = None
    try:
        client = docker.from_env()
        container = client.containers.run(
            # 使用当前项目镜像，因为其中已经安装 pytest。
            image=os.getenv("SANDBOX_TEST_IMAGE", "myagent:latest"),
            command=["python", "-c", runner],
            environment={
                "FUNCTION_CODE": encoded_function,
                "TEST_CODE": encoded_test,
            },
            mem_limit="256m",                    # pytest 最多使用 256MB 内存
            nano_cpus=500_000_000,                # 最多使用 0.5 个 CPU 核心
            pids_limit=64,                        # 限制测试创建的进程数量
            network_disabled=True,                # 测试期间禁止访问网络
            read_only=True,                       # 根文件系统只读
            tmpfs={"/tmp": "rw,noexec,nosuid,size=32m"},  # 仅允许写入临时目录
            cap_drop=["ALL"],                     # 删除 Linux 额外权限
            security_opt=["no-new-privileges"],   # 禁止进程提升权限
            detach=True,
        )

        try:
            # 单元测试最多运行 30 秒。
            result = container.wait(timeout=60)
        except Exception:
            container.kill()
            return "测试超时（30秒）"

        output = container.logs(stdout=True, stderr=True).decode(
            "utf-8",
            errors="replace",
        ).strip()

        # StatusCode == 0 代表测试代码自身运行成功，但是业务代码被测试的结果，可能存在bug
        if result.get("StatusCode") == 0:
            return f"测试成功：\n{output or '无输出'}"
        return f"测试失败：\n{output or '无输出'}"
    except Exception as error:
        return f"测试异常：{error}"
    finally:
        # 测试结束后删除一次性沙箱容器。
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass


# 根据需求，生成业务代码
def generate_code(requirement: str, error_feedback: str = "") -> str:
    """根据需求生成代码；若有错误反馈，则让模型修正代码。"""
    template = """
你是一名 Python 程序员，请根据需求编写代码。

需求：{requirement}

{feedback}
代码必须能够自行执行结束，禁止无限循环、等待用户输入和启动常驻服务。
只输出完整的 Python 代码，不要解释，不要 Markdown。
"""
    feedback_text = ""
    if error_feedback:
        feedback_text = (
            f"上一版代码执行报错：\n{error_feedback}\n"
            "请修正代码，只输出修正后的完整代码。"
        )

    # 把上面的模板转换成 LangChain 可调用的提示词
    prompt = PromptTemplate.from_template(template)
    # `prompt | llm`：提示词先填充参数，再交给大模型生成代码
    response = (prompt | llm).invoke(
        {"requirement": requirement, "feedback": feedback_text}
    )
    # 清理模型可能返回的 Markdown 代码块标记
    return _clean_code(response.content)


# 根据业务代码，生成单元测试代码
# 根据业务代码 function_code 生成测试代码，因为测试代码里肯定会包含一段代码，这段代码就是导入业务代码，调用这个业务代码写测试用例，
# 所以让测试代码从 target.py 里导入这段业务代码 from target import target,py
def generate_test(function_code: str, error_feedback: str = "") -> str:
    """针对 target.py 中的业务代码生成 pytest 测试。"""
    template = """
针对下面保存在 target.py 中的 Python 业务代码，生成 pytest 单元测试。

业务代码：
{function_code}

Important test-generation rules:
- Import only functions or classes from `target`; do not import or test module-level
  objects that may already have executed while `target` was imported.
- Do not test real waiting duration, sleeping, interactive input, infinite loops,
  background services, or other wall-clock timing behavior.
- For timers, sleeps, time calls, input, network, and other side effects, use
  `pytest` monkeypatch or `unittest.mock` so tests complete immediately.
- Test reusable functions/classes and their observable behavior. If the supplied
  code only contains top-level execution and has no safely testable reusable API,
  write a test that runs it with the relevant dependency mocked; never reuse an
  already-finished global timer/thread/process.

要求：
1. 测试代码必须使用 `from target import ...` 导入需要测试的对象。
2. 禁止使用 your_module 或其他不存在的占位模块名。
3. 覆盖正常情况和边界情况，至少 3 个测试用例。
4. 不要把业务代码重复写进测试代码。
5. 只输出可直接保存为 test_target.py 的完整测试代码，不要解释，不要 Markdown。

{feedback}
"""
    feedback_text = ""
    if error_feedback:
        feedback_text = (
            f"上一版测试执行失败：\n{error_feedback}\n"
            "请根据报错修正测试代码。"
        )

    prompt = PromptTemplate.from_template(template)
    response = (prompt | llm).invoke(
        {"function_code": function_code, "feedback": feedback_text}
    )
    return _clean_code(response.content)


def code_agent(requirement: str, mode: str = "code", max_attempts: int = 3):
    """
    mode="code"：生成业务代码并运行验证。
    mode="test"：把 requirement 当作业务代码，生成测试并用 pytest 验证。
    """
    if mode == "code":
        code = generate_code(requirement)
        result = ""
        for attempt in range(1, max_attempts + 1):
            result = run_code(code)
            # 执行成功 代表业务代码自身运行成功
            if result.startswith("执行成功"):
                return {
                    "code": code,
                    "result": result,
                    "attempts": attempt,
                    "status": "success",
                }
            if attempt < max_attempts:
                code = generate_code(requirement, result)
        return {
            "code": code,
            "result": result,
            "attempts": max_attempts,
            "status": "failed",
        }

    if mode == "test":
        test_code = generate_test(requirement)
        result = ""
        for attempt in range(1, max_attempts + 1):
            result = run_tests(requirement, test_code)
            # 测试成功 代表测试代码自身运行成功，但是业务代码被测试的结果，可能存在bug
            if result.startswith("测试成功"):
                return {
                    "test_code": test_code,
                    "result": result,
                    "attempts": attempt,
                    "status": "success",
                }
            if attempt < max_attempts:
                test_code = generate_test(requirement, result)
        return {
            "test_code": test_code,
            "result": result,
            "attempts": max_attempts,
            "status": "failed",
        }

    raise ValueError("mode 只能是 'code' 或 'test'")
