import base64
import io
import re

from PIL import Image, ImageDraw, ImageFont


def normalize_question_number(number) -> str:
    """把1、第1题、1.等题号统一成1。"""
    text = str(number).strip()
    match = re.search(r"\d+", text)
    return match.group() if match else text.replace("第", "").replace("题", "")


def draw_grading_result(image_bytes: bytes, positions: list, grading_result: dict) -> str:
    """把每道题的对错和得分画到学生试卷上，返回图片Base64。"""

    # 把图片字节流转为PIL图像对象，并转为RGB模式
    original_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # 获取原试卷图片宽高
    width, height = original_image.size
    # 在试卷右侧增加固定白色批注区，避免批改内容遮挡原试卷。
    margin_width = 900
    image = Image.new("RGB", (width + margin_width, height), "white")
    image.paste(original_image, (0, 0))
    # 创建绘图对象，用于在图片上画批注
    draw = ImageDraw.Draw(image)
    # Docker镜像中安装的中文字体，用来正常显示中文批改说明。
    font = ImageFont.truetype(
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        28,
    )
    # 在右侧批注区顶部绘制总分。
    draw.text(
        (width + 20, 20),
        f"总分：{grading_result.get('total_score', 0)}",
        fill="red",
        font=font,
    )

    # 用批改的结果构建数据 { 题号1: 批改结果1 ,题号2: 批改结果2}
    results = {
        normalize_question_number(item.get("number")): item
        for item in grading_result.get("questions", [])
    }

    for position in positions:
        result = results.get(normalize_question_number(position.get("number")))
        if not result:
            continue

        # 这就是抽离出每道题的坐标，在坐标位置打分、画勾叉   至于为什么/1000 是因为 OCR 识别的坐标，他是把所有图片看成1000大小，其实不用管这么多，就知道前面那句话就行
        bbox = position.get("bbox", [])
        if len(bbox) == 4:
            left, top, right, bottom = bbox
        elif len(bbox) == 5:
            # 视觉模型有时返回：中心点X、中心点Y、高度、宽度、角度。
            center_x, center_y, box_height, box_width, _ = bbox
            left = center_x - box_width / 2
            top = center_y - box_height / 2
            right = center_x + box_width / 2
            bottom = center_y + box_height / 2
        elif len(bbox) >= 8:
            # 有些视觉模型返回四个顶点，共8个数字，把它转成左、上、右、下。
            left = min(bbox[0::2])
            top = min(bbox[1::2])
            right = max(bbox[0::2])
            bottom = max(bbox[1::2])
        else:
            continue

        left = int(left * width / 1000)
        top = int(top * height / 1000)
        right = int(right * width / 1000)
        bottom = int(bottom * height / 1000)

        # 防止视觉模型把左右或上下坐标顺序返回反了。
        left, right = sorted((left, right))
        top, bottom = sorted((top, bottom))

        color = "green" if result.get("is_correct") else "red"
        # 所有批注使用相同的横坐标，在右侧批注区整齐对齐。
        mark_x = width + 20
        mark_y = top

        # 用线条画勾或叉，不依赖服务器字体。
        if result.get("is_correct"):
            draw.line((mark_x, mark_y + 10, mark_x + 7, mark_y + 18), fill=color, width=3)
            draw.line((mark_x + 7, mark_y + 18, mark_x + 23, mark_y), fill=color, width=3)
        else:
            draw.line((mark_x, mark_y, mark_x + 20, mark_y + 20), fill=color, width=3)
            draw.line((mark_x + 20, mark_y, mark_x, mark_y + 20), fill=color, width=3)

        # 在勾叉后面依次显示得分和批改说明。
        note = f"{result.get('score', 0)}分  {result.get('feedback', '')}"
        # 批改说明过长时换行，避免超出右侧批注区。
        note = "\n".join(note[index:index + 26] for index in range(0, len(note), 26))
        draw.multiline_text(
            (mark_x + 30, mark_y),
            note,
            fill=color,
            font=font,
            spacing=6,
        )

    # 创建一个缓冲区，用于临时存储图片数据，不写入磁盘。
    output = io.BytesIO()
    # 保存图片
    image.save(output, format="JPEG")

    # 把图片以base64格式返回。前端拿到后可以解码显示（如 `<img src="data:image/jpeg;base64,{数据}">`），还原成图片。
    return base64.b64encode(output.getvalue()).decode("utf-8")


# 画图逻辑
# 让大模型识图，输出每张图上每道题的坐标、题号
# 大模型批改作业的输出结果要求带有题号
# 这样根据题号相同，就能找出 每道题坐标 对应的 批改结果
# 调用绘图对象，在每道题坐标上绘画出对应的作业批改结果
