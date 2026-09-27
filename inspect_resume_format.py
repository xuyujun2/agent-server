import json
from docx import Document


doc = Document("resume_source.docx")

styles = {}
for style_name in ["Normal", "Normal (Web)", "Resume Heading", "Job Title", "List Bullet"]:
    style = doc.styles[style_name]
    pf = style.paragraph_format
    styles[style_name] = {
        "font_name": style.font.name,
        "font_size_pt": style.font.size.pt if style.font.size else None,
        "bold": style.font.bold,
        "space_before_pt": pf.space_before.pt if pf.space_before else None,
        "space_after_pt": pf.space_after.pt if pf.space_after else None,
        "line_spacing": pf.line_spacing,
        "left_indent_pt": pf.left_indent.pt if pf.left_indent else None,
        "first_line_indent_pt": pf.first_line_indent.pt if pf.first_line_indent else None,
        "keep_with_next": pf.keep_with_next,
        "page_break_before": pf.page_break_before,
    }

paragraphs = []
for i, p in enumerate(doc.paragraphs):
    if not p.text.strip():
        continue
    pf = p.paragraph_format
    runs = []
    for r in p.runs:
        if r.text:
            runs.append({
                "text": r.text,
                "font": r.font.name,
                "size": r.font.size.pt if r.font.size else None,
                "bold": r.bold,
                "color": str(r.font.color.rgb) if r.font.color and r.font.color.rgb else None,
            })
    paragraphs.append({
        "index": i,
        "style": p.style.name,
        "text": p.text,
        "alignment": str(p.alignment),
        "space_before": pf.space_before.pt if pf.space_before else None,
        "space_after": pf.space_after.pt if pf.space_after else None,
        "line_spacing": pf.line_spacing,
        "left_indent": pf.left_indent.pt if pf.left_indent else None,
        "first_line_indent": pf.first_line_indent.pt if pf.first_line_indent else None,
        "keep_with_next": pf.keep_with_next,
        "keep_together": pf.keep_together,
        "page_break_before": pf.page_break_before,
        "runs": runs,
    })

print(json.dumps({"styles": styles, "paragraphs": paragraphs}, ensure_ascii=False, indent=2))
