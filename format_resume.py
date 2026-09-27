from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


SOURCE = r"C:\Users\28763\Desktop\徐玉俊-AI Agent开发工程师简历.docx"
OUTPUT = r"C:\Users\28763\Desktop\agent\customer_service_agent\徐玉俊-AI Agent开发工程师简历-排版修正版.docx"


def set_font(run, size=None, bold=None, color=None):
    run.font.name = "Arial"
    fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:ascii"), "Arial")
    fonts.set(qn("w:hAnsi"), "Arial")
    fonts.set(qn("w:cs"), "Arial")
    fonts.set(qn("w:eastAsia"), "微软雅黑")
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)
    r_pr = run._element.get_or_add_rPr()
    for tag in ("w:shd", "w:highlight"):
        element = r_pr.find(qn(tag))
        if element is not None:
            r_pr.remove(element)


doc = Document(SOURCE)

for section in doc.sections:
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.25)
    section.bottom_margin = Cm(1.25)
    section.left_margin = Cm(1.65)
    section.right_margin = Cm(1.65)
    section.header_distance = Cm(0.6)
    section.footer_distance = Cm(0.6)

styles = doc.styles
for style_name in ("Normal", "Normal (Web)", "List Bullet"):
    if style_name in styles:
        style = styles[style_name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        style.font.size = Pt(9)

for paragraph in doc.paragraphs:
    style_name = paragraph.style.name
    fmt = paragraph.paragraph_format
    fmt.widow_control = True

    if not paragraph.text.strip():
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(0)
        fmt.line_spacing = Pt(1)
        continue

    if style_name == "Resume Heading":
        fmt.space_before = Pt(8)
        fmt.space_after = Pt(3)
        fmt.line_spacing = 1
        fmt.keep_with_next = True
        for run in paragraph.runs:
            set_font(run, 14, True, (20, 78, 125))
    elif style_name == "Job Title":
        fmt.space_before = Pt(7)
        fmt.space_after = Pt(2)
        fmt.line_spacing = 1.05
        fmt.keep_with_next = True
        for run in paragraph.runs:
            set_font(run, 10.5)
    elif style_name == "List Bullet":
        fmt.left_indent = Cm(0.55)
        fmt.first_line_indent = Cm(-0.35)
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(1.5)
        fmt.line_spacing = 1.12
        for run in paragraph.runs:
            set_font(run, 9)
    elif style_name == "Normal (Web)":
        fmt.left_indent = Cm(0.18)
        fmt.first_line_indent = Cm(0)
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(1.2)
        fmt.line_spacing = 1.12
        for run in paragraph.runs:
            set_font(run, 9)
    else:
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(1.5)
        fmt.line_spacing = 1.12
        for run in paragraph.runs:
            set_font(run, 9)

    text = paragraph.text.strip()
    if text.startswith("项目："):
        fmt.space_before = Pt(3)
        fmt.keep_with_next = True
    elif text.startswith(("项目描述：", "工作内容：", "技术栈：")):
        fmt.space_before = Pt(1)

# 姓名、求职方向、联系方式
if len(doc.paragraphs) >= 3:
    for index, size, bold, after in ((0, 24, True, 1), (1, 12.5, True, 3), (2, 9.5, False, 6)):
        paragraph = doc.paragraphs[index]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(after)
        paragraph.paragraph_format.line_spacing = 1
        for run in paragraph.runs:
            set_font(run, size, bold, (0, 0, 0))

doc.save(OUTPUT)
print(OUTPUT)
