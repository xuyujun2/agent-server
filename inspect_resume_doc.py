from pathlib import Path
from collections import Counter

from docx import Document


path = Path("resume_source.docx")
doc = Document(path)

print(f"paragraphs={len(doc.paragraphs)} tables={len(doc.tables)} sections={len(doc.sections)}")
print("styles:", Counter(p.style.name for p in doc.paragraphs))
for i, p in enumerate(doc.paragraphs):
    text = p.text.replace("\t", "<TAB>").replace("\n", "<BR>")
    if text.strip():
        print(f"P{i:03d} [{p.style.name}] align={p.alignment} {text}")

for ti, table in enumerate(doc.tables):
    print(f"TABLE {ti}: {len(table.rows)}x{len(table.columns)}")
    for ri, row in enumerate(table.rows):
        vals = [cell.text.replace("\n", "<BR>") for cell in row.cells]
        print(f"  R{ri}: {vals}")
