import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agents.grading_agent import executor
from app.services.grading.grading_image_service import draw_grading_result
from app.services.grading.vision_service import recognize_image

router = APIRouter(prefix="/grading", tags=["作业批改"])


@router.post("/upload")
async def upload_and_grade(
    answer_image: list[UploadFile] = File(...),
    student_image: list[UploadFile] = File(...),
    rules: str = Form(""),
):
    """上传标准答案和学生试卷图片，返回文字结果和批改图片。"""
    try:
        answer_pages = []
        for page_number, image in enumerate(answer_image, start=1):
            image_bytes = await image.read()
            recognized = recognize_image(image_bytes, image.content_type or "image/png")
            # 使用每道题的text拼成这一页的识别文字，为了兜底 full_text 有时候识别不到
            questions_text = "\n\n".join(
                item.get("text", "").strip()
                for item in recognized.get("questions", [])
                if item.get("text", "").strip()
            )
            page_text = recognized.get("full_text", "").strip() or questions_text
            answer_pages.append(
                f"第{page_number}页：\n{page_text}"
            )

        student_images = []
        student_pages = []
        for page_number, image in enumerate(student_image, start=1):
            # 读取上传图片文件的 二进制内容，存到 image_bytes 变量里   一张整图
            image_bytes = await image.read()
            recognized = recognize_image(image_bytes, image.content_type or "image/png")
            # tudent_images =>  [{"image_bytes": 每张图的二进制数据,  "positions": 每张图上题目的位置和题号}]
            student_images.append({
                "image_bytes": image_bytes,
                "positions": recognized.get("questions", []),
            })

            questions_text = "\n\n".join(
                item.get("text", "").strip()
                for item in recognized.get("questions", [])
                if item.get("text", "").strip()
            )
            page_text = recognized.get("full_text", "").strip() or questions_text
            student_pages.append(
                f"第{page_number}页：\n{page_text}"
            )

        answer_text = "\n\n".join(answer_pages)
        student_text = "\n\n".join(student_pages)

        agent_input = f"""请判断是作文还是数学，并批改作业。

标准答案识别文字：
{answer_text}

评分规则：
{rules or "未提供，请使用对应类型的默认评分规则"}

学生试卷识别文字：
{student_text}
"""
        result = executor.invoke({"input": agent_input})
        # 去掉markdown标记，删除开头、结尾的````       strip() 删除空格、换行
        result_text = result["output"].replace("```json", "").replace("```", "").strip()
        grading_result = json.loads(result_text)
        question_scores = [
            item.get("score", 0)
            for item in grading_result.get("questions", [])
        ]
        # 总分由程序按逐题得分相加，避免模型把总分算错。
        grading_result["total_score"] = sum(question_scores)

        graded_images = [
            # 三个参数依次是 每张图的二进制数据、每张图上题目的位置和题号、AI批改作业的所有回复    理解关键节点的数据结构，就能容易理解
            draw_grading_result(page["image_bytes"], page["positions"], grading_result)
            for page in student_images
        ]

        return {
            "code": 0,
            "data": {
                "answer": grading_result,
                "graded_images": graded_images,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
