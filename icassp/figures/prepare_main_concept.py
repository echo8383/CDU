"""Make a vector-preserving paper export of the editable main figure.

The full Draw.io export is kept as main_concept_full.pdf. Re-export the
Draw.io source to that file before rerunning this script after future edits.
"""

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject
from reportlab.pdfgen import canvas


HERE = Path(__file__).resolve().parent
source = HERE / "main_concept_full.pdf"
target = HERE / "main_concept.pdf"

reader = PdfReader(source)
if len(reader.pages) != 1:
    raise ValueError("Expected a one-page Draw.io export")
page = reader.pages[0]
width = float(page.mediabox.width)

# Retain the author's purple title banner, scientific panels, and bottom labels.
# Trim only two points of blank space above the figure.
bottom, top = 0.0, 490.0

# Correct the singular label in the historical export. The corresponding
# editable label is also corrected in main_concept.drawio.
buffer = BytesIO()
overlay = canvas.Canvas(buffer, pagesize=(width, float(page.mediabox.height)))
overlay.setFillColorRGB(1, 1, 1)
overlay.rect(73, 170, 143, 19, stroke=0, fill=1)
overlay.setFillColorRGB(17 / 255, 27 / 255, 59 / 255)
overlay.setFont("Times-Bold", 13.2)
overlay.drawString(78, 175, "Statistical reference")
overlay.setFont("Times-BoldItalic", 13.2)
overlay.drawString(194, 175, "B")
overlay.save()
buffer.seek(0)
page.merge_page(PdfReader(buffer).pages[0])

box = RectangleObject((0, bottom, width, top))
page.mediabox = box
page.cropbox = box
writer = PdfWriter()
writer.add_page(page)
writer.pdf_header = "%PDF-1.5"
with target.open("wb") as output:
    writer.write(output)

print(f"Wrote {target} ({width:.0f} x {top - bottom:.0f} pt)")
