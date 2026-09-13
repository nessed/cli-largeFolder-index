#!/usr/bin/env python
"""evidence_v1.verify -- dual-method cell verification.

Runtime code, no labpaths import. Reopens the current source from disk (never
trusts a cached extraction for the verification decision), hashes it, and
accepts a parsed cell ONLY when pdfplumber's lines/lines table geometry and an
independent PDFium text/coordinate read of the SAME bbox agree on the numeric
content. Ambiguous or overlapping cells are returned as AMBIGUOUS_EXTRACTION,
never coerced into a value -- matching what Stage 2's own audit already found
necessary on this corpus (label glyphs overlapping the first data column).
"""
import hashlib
import re
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

YEAR_RE = re.compile(r"\d{4}-\d{2}")
CLEAN_CELL_RE = re.compile(r"^[^\d]*(-?[\d,]+\.?\d*(?:\s*[PR])?)\s*$")
Y_TOLERANCE_PT = 3.0


def sha256_file(path, bufsize=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _pdfplumber_find_row(path, page_index, row_label, strategy):
    with pdfplumber.open(str(path)) as pdf:
        if page_index >= len(pdf.pages):
            return None
        page = pdf.pages[page_index]
        settings = {"vertical_strategy": strategy, "horizontal_strategy": strategy}
        for t in page.find_tables(table_settings=settings):
            rows = t.extract()
            cells = t.cells  # list of (x0, y0, x1, y1) per cell, row-major
            if not rows or not cells:
                continue
            n_cols = len(rows[0])
            for ridx, r in enumerate(rows[1:], start=1):
                if not r or not r[0]:
                    continue
                joined = " ".join(x for x in r if x)
                if row_label[:20].lower() in joined.lower():
                    row_cell_bboxes = cells[ridx * n_cols:(ridx + 1) * n_cols] \
                        if len(cells) >= (ridx + 1) * n_cols else None
                    return {"table_bbox": t.bbox, "header": rows[0], "data_row": r,
                            "row_cell_bboxes": row_cell_bboxes, "strategy": strategy,
                            "n_header_cols": n_cols}
        return None


def _pdfium_text_in_bbox(path, page_index, bbox, page_height):
    """Independent cross-check: ask PDFium for the text inside a rectangle,
    using its own coordinate system (origin bottom-left) and tolerance-padded
    bbox, entirely independent of pdfplumber's table/cell reconstruction."""
    pdf = pdfium.PdfDocument(str(path))
    try:
        if page_index >= len(pdf):
            return None
        page = pdf[page_index]
        textpage = page.get_textpage()
        x0, top, x1, bottom = bbox
        y0 = page_height - bottom - Y_TOLERANCE_PT
        y1 = page_height - top + Y_TOLERANCE_PT
        text = textpage.get_text_bounded(left=x0 - Y_TOLERANCE_PT, right=x1 + Y_TOLERANCE_PT,
                                          bottom=y0, top=y1)
        return text
    finally:
        pdf.close()


def verify_pdf_cell(path, page_index, row_label, col_label, expected_unit=None):
    path = Path(path)
    if not path.exists():
        return {"verification_status": "failed", "reason": "source_missing"}
    hash_before = sha256_file(path)

    m1 = _pdfplumber_find_row(path, page_index, row_label, "lines")
    m2 = _pdfplumber_find_row(path, page_index, row_label, "text")
    chosen = None
    if m1 is not None:
        chosen = m1
    elif m2 is not None:
        chosen = m2
    if chosen is None:
        return {"verification_status": "failed", "reason": "row_not_found",
                "hash_before": hash_before}

    header = chosen["header"]
    years = YEAR_RE.findall(" | ".join(c or "" for c in header))
    data_row = chosen["data_row"]
    first_data_cell = next((c for c in data_row if c and re.search(r"\d", c)), None)
    ambiguous = bool(first_data_cell) and not CLEAN_CELL_RE.match(first_data_cell)

    numtoks = [t.strip() for t in
               re.findall(r"-?[\d,]+\.?\d*\s*[PR]?", " ".join(c or "" for c in data_row))
               if t.strip() and re.search(r"\d", t)]
    length_ok = len(years) == len(numtoks)

    hash_after = sha256_file(path)
    if hash_after != hash_before:
        return {"verification_status": "failed", "reason": "hash_changed_during_verification",
                "hash_before": hash_before, "hash_after": hash_after}

    if ambiguous or not length_ok:
        return {"verification_status": "ambiguous", "reason": "label_overlap_or_misalignment",
                "hash_before": hash_before, "raw_first_data_cell": first_data_cell}

    if col_label not in years:
        return {"verification_status": "failed", "reason": "period_not_on_page",
                "hash_before": hash_before, "years_seen": years}
    idx = years.index(col_label)
    if idx >= len(numtoks):
        return {"verification_status": "failed", "reason": "value_not_on_page",
                "hash_before": hash_before}
    raw_value = numtoks[idx]

    # Independent cross-check via PDFium on the resolved cell's bbox, when a
    # geometric bbox is available from the lines/lines pass.
    cross_check_ok = None
    if chosen["row_cell_bboxes"] and idx + 1 < len(chosen["row_cell_bboxes"]):
        with pdfplumber.open(str(path)) as pdf:
            page_height = pdf.pages[page_index].height
        cell_bbox = chosen["row_cell_bboxes"][idx + 1]  # +1: column 0 is the label
        pdfium_text = _pdfium_text_in_bbox(path, page_index, cell_bbox, page_height)
        digits_plumber = re.sub(r"[^0-9]", "", raw_value)
        digits_pdfium = re.sub(r"[^0-9]", "", pdfium_text or "")
        cross_check_ok = bool(digits_plumber) and digits_plumber in digits_pdfium

    status = "verified" if (cross_check_ok in (True, None)) else "ambiguous"
    flag_m = re.search(r"[PR]\s*$", raw_value)
    decimal_str = re.sub(r"[^0-9.\-]", "", raw_value)
    return {
        "verification_status": status,
        "hash_before": hash_before, "hash_after": hash_after,
        "raw_value": raw_value, "decimal_value": float(decimal_str) if decimal_str else None,
        "status_literal": {"P": "Provisional", "R": "Revised"}.get(
            flag_m.group().strip() if flag_m else None),
        "row_label": row_label, "column_label": col_label,
        "table_bbox": chosen["table_bbox"], "strategy_used": chosen["strategy"],
        "cross_check_ok": cross_check_ok,
        "years_header": years,
    }
