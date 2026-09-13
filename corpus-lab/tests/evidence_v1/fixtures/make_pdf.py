#!/usr/bin/env python
"""Hand-built minimal PDF writer for test fixtures -- no reportlab/fpdf
dependency. Produces a valid single-xref-table PDF with N pages; a page with
text=None gets an empty content stream (renders as no extractable text, for
simulating a scanned/blank page); a page with text="..." gets a real BT/Tj
text block pdftotext can read. Never used for anything but locally authored,
gold-free fixture files.
"""


def _obj(n, body):
    return "{} 0 obj\n{}\nendobj\n".format(n, body)


def build_pdf(page_texts, encrypt_owner_password=None):
    n_pages = len(page_texts)
    objects = {}
    objects[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join("{} 0 R".format(3 + 2 * i) for i in range(n_pages))
    objects[2] = "<< /Type /Pages /Kids [{}] /Count {} >>".format(kids, n_pages)

    content_obj_ids = []
    for i, text in enumerate(page_texts):
        page_obj_id = 3 + 2 * i
        content_obj_id = page_obj_id + 1
        content_obj_ids.append(content_obj_id)
        objects[page_obj_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
            "/Resources << /Font << /F1 {} 0 R >> >> /Contents {} 0 R >>"
        ).format(3 + 2 * n_pages, content_obj_id)
        if text:
            escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            stream = "BT /F1 12 Tf 20 150 Td ({}) Tj ET".format(escaped)
        else:
            stream = ""
        objects[content_obj_id] = "<< /Length {} >>\nstream\n{}\nendstream".format(
            len(stream), stream)

    font_obj_id = 3 + 2 * n_pages
    objects[font_obj_id] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    out = bytearray()
    out += b"%PDF-1.4\n"
    offsets = {}
    for n in sorted(objects.keys()):
        offsets[n] = len(out)
        out += _obj(n, objects[n]).encode("latin-1")

    xref_offset = len(out)
    max_obj = max(objects.keys())
    out += "xref\n0 {}\n".format(max_obj + 1).encode("latin-1")
    out += b"0000000000 65535 f \n"
    for n in range(1, max_obj + 1):
        if n in offsets:
            out += "{:010d} 00000 n \n".format(offsets[n]).encode("latin-1")
        else:
            out += b"0000000000 65535 f \n"
    out += (
        "trailer\n<< /Size {} /Root 1 0 R >>\nstartxref\n{}\n%%EOF"
    ).format(max_obj + 1, xref_offset).encode("latin-1")
    return bytes(out)


def write_pdf(path, page_texts):
    data = build_pdf(page_texts)
    with open(path, "wb") as f:
        f.write(data)


def write_encrypted_pdf(path, page_texts, user_password="secret"):
    """Build a plain PDF then re-save it encrypted via pypdf (pypdf CAN write
    encryption even though it cannot author rich content streams)."""
    import io
    import pypdf
    plain = build_pdf(page_texts)
    reader = pypdf.PdfReader(io.BytesIO(plain))
    writer = pypdf.PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
    writer.encrypt(user_password=user_password, owner_password=None)
    with open(path, "wb") as f:
        writer.write(f)
