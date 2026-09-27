from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


SOURCE = Path("resume_source.docx")
OUTPUT = Path("徐玉俊-AI Agent开发工程师简历-格式修正版.docx")

BLUE = RGBColor(0x1F, 0x4E, 0x79)
DARK = RGBColor(0x26, 0x26, 0x26)
GRAY = RGBColor(0x59, 0x59, 0x59)


def set_font(run, size=9, bold=False, color=DARK):
    run.font.name = "Arial"
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), "微软雅黑")
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def remove_shading(element):
    ppr = element.find(qn("w:pPr"))
    if ppr is not None:
        for node in list(ppr.findall(qn("w:shd"))):
            ppr.remove(node)


def remove_paragraph(paragraph):
    parent = paragraph._element.getparent()
    parent.remove(paragraph._element)


def rewrite_labeled_paragraph(paragraph, label, rest_color=DARK):
    text = paragraph.text
    rest = text[len(label):]
    for run in list(paragraph.runs):
        paragraph._element.remove(run._element)
    label_run = paragraph.add_run(label)
    set_font(label_run, bold=True, color=BLUE)
    if rest:
        rest_run = paragraph.add_run(rest)
        set_font(rest_run, color=rest_color)


doc = Document(SOURCE)

# 删除多余空段落，避免项目之间出现不一致的大空白。
for paragraph in list(doc.paragraphs):
    if not paragraph.text.strip():
        remove_paragraph(paragraph)

label_rules = {
    "项目：": (Pt(2), Pt(1.2), True, DARK),
    "项目描述：": (Pt(0.5), Pt(1.2), False, DARK),
    "负责内容：": (Pt(0), Pt(1.2), False, DARK),
    "技术栈：": (Pt(0.5), Pt(1.2), False, GRAY),
}

for paragraph in doc.paragraphs:
    text = paragraph.text.strip()
    pf = paragraph.paragraph_format
    remove_shading(paragraph._element)

    if paragraph.style.name == "Normal (Web)":
        paragraph.style = doc.styles["Normal"]

    if paragraph.style.name == "Resume Heading":
        pf.space_before = Pt(6)
        pf.space_after = Pt(2.5)
        pf.line_spacing = 1.0
        pf.keep_with_next = True
        pf.keep_together = True
        pf.page_break_before = False
        for run in paragraph.runs:
            set_font(run, size=14, bold=True, color=RGBColor(0x14, 0x4E, 0x7D))
        continue

    if paragraph.style.name == "Job Title":
        pf.space_before = Pt(6)
        pf.space_after = Pt(2)
        pf.line_spacing = 1.03
        pf.keep_with_next = True
        pf.keep_together = True
        pf.page_break_before = False
        continue

    if paragraph.style.name == "List Bullet":
        pf.space_after = Pt(1.2)
        pf.line_spacing = 1.08
        for run in paragraph.runs:
            set_font(run, size=9, bold=False, color=DARK)
        continue

    if paragraph.style.name == "Normal":
        pf.space_after = Pt(1.2)
        pf.line_spacing = 1.08
        if paragraph.alignment not in (WD_ALIGN_PARAGRAPH.CENTER,):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

    matched = False
    for label, (before, after, keep_next, rest_color) in label_rules.items():
        if text.startswith(label):
            rewrite_labeled_paragraph(paragraph, label, rest_color)
            pf.left_indent = Pt(5.1)
            pf.first_line_indent = Pt(0)
            pf.space_before = before
            pf.space_after = after
            pf.line_spacing = 1.08
            pf.keep_with_next = keep_next
            pf.keep_together = True
            matched = True
            break

    if matched:
        continue

    # 内容管理后台项目原有的明细行补齐统一缩进和正文样式。
    if text.startswith(("书城管理：", "书籍管理：", "详情页配置：", "章节管理：", "基于Django ORM", "基于MySQL")):
        pf.left_indent = Pt(5.1)
        pf.first_line_indent = Pt(0)
        pf.space_before = Pt(0)
        pf.space_after = Pt(1.2)
        pf.line_spacing = 1.08
        pf.keep_together = True
        for run in paragraph.runs:
            set_font(run, size=9, bold=False, color=DARK)

# 确保页脚样式统一，不改变原文字。
for section in doc.sections:
    for paragraph in section.footer.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            set_font(run, size=8, bold=False, color=GRAY)

doc.save(OUTPUT)
print(OUTPUT.resolve())
