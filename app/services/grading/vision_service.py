import base64
import json

from openai import OpenAI

from app.config import Config


def recognize_image(image_bytes: bytes, content_type: str) -> dict:
    """识别试卷文字和每道题的位置，不进行批改。"""
    client = OpenAI(
        api_key=Config.VISION_API_KEY,
        base_url=Config.VISION_BASE_URL,
    )
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # 视觉API = base_url + api_key + model 三者组合
    # client.chat.completions.create() 和 llm.invoke() 只是两种不同 SDK 的调用方式，作用基本相同
    # 这里是 OpenAI SDK，之前用的是 LangChain 的 ChatOpenAI SDK 
    # 提示词 content 写法区别: llm.invoke() 用 (),(),()，   client.chat.completions.create() 用 {},{},{}
    # "role": "user"：标识消息是用户的输入
    # "type": "text"：告诉模型这部分是文字      "type": "image_url"：告诉模型这部分是图片
    # response_format={"type": "json_object"}   告诉视觉模型：返回内容必须是合法 JSON，不能返回解释、Markdown或格式错误的普通文本
    # max_tokens=8000：限制模型最多返回8000个token
    prompt = (
                            "请识别试卷中的每道题和答案，并给出每道题在图片中的位置。"
                            "full_text必须从图片顶部到图片底部完整抄录所有可见文字，不能留空，不能省略题目、答案或解题过程。"
                            "即使本页开头没有题号，也必须把页首出现的‘学生解：’、计算过程、公式和答案完整写入full_text，绝对不能省略。"
                            "如果本页开头是无题号的解题过程，后面才出现新题号，页首内容属于上一页最后一题的续写答案；必须保留在full_text中，不能归入后面的新题。"
                            "括号、横线或答题区域中已经填写的内容就是该题答案，不能判成未作答。"
                            "答案必须按图片完整抄录，不能漏掉数字、根、选项或计算步骤；"
                            "必须从图片顶部扫描到图片底部，所有能看到明确题号的题目都必须放入questions，不能遗漏。"
                            "只有‘数字+英文句点.’格式才识别为题号，例如‘19.’；‘46分’‘3分’、页码、公式中的数字和章节标题都不是题号。"
                            "每一道真实题目都必须返回number、text和bbox，不能只识别文字却遗漏该题坐标。"
                            "在标准答案图片中，题号后出现的‘答案：’‘解：’‘解析：’‘参考答案：’之后的内容，都属于该题标准答案。"
                            "解答题没有‘答案：’时，‘解：’后面的完整计算过程和最终结论就是标准答案。"
                            "遇到下一题题号，才表示上一题答案结束。"
                            "不得因为没有‘答案：’三个字，就判断标准答案缺失。"
                            "如果是作文，题号统一写作文，坐标使用整篇作文的位置。"
                            "questions中的text必须完整抄录当前题的题目、选项、答案和解题过程，不能留空。"
                            "坐标使用0到1000的整数。每个bbox必须且只能包含4个值，"
                            "依次是左、上、右、下，并且只框住当前这一道题。只返回JSON："
                            '{"full_text":"完整文字","questions":['
                            '{"number":"题号","text":"当前题的完整文字","bbox":[左,上,右,下]}]}'
    )

    response = client.chat.completions.create(
        model=Config.VISION_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{content_type};base64,{image_base64}"
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=8000,
    )

    result_text = response.choices[0].message.content or "{}"
    # 去掉模型有时附带的 ```json 和 ```。
    result_text = result_text.replace("```json", "").replace("```", "").strip()
    return json.loads(result_text)




# result_text = '''
# {
#   "full_text": "1. 计算 2+3。学生答案：5\n2. 计算 6×4。学生答案：20",
#   "questions": [
#     {
#       "number": "1",
#       "bbox": [100, 120, 800, 260]
#     },
#     {
#       "number": "2",
#       "bbox": [100, 320, 800, 460]
#     }
#   ]
# }
# '''
