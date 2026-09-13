#!/usr/bin/env python
"""evidence_v1.extract -- per-file text/table extraction adapters.

Runtime code, no labpaths import. Each extractor returns a uniform shape:
    {"format": str, "n_pages": int|None, "n_text_pages": int|None,
     "status": <file status enum>, "error_class": str|None,
     "pages": [{"page_index": int, "text_status": str, "raw_text": str}],
     "tables": [table-card dicts, pre-caption-detection for PDF text]}

File statuses (contract-fixed): readable, partially_readable, no_text, empty,
encrypted, parser_failed, unsupported, excluded, pending, vanished.
"""
import csv
import io
import re
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

EXTRACTOR_VERSIONS = {"pdftotext": "xpdf-4.00", "pdfplumber": "0.11.10",
                       "pypdfium2": "5.13.0", "pypdf": "6.18.1", "csv": "stdlib",
                       "docx": "stdlib-zip-xml", "xlsx": "stdlib-zip-xml"}

TEXT_UNIT_LINES = 80
TEXT_UNIT_OVERLAP = 10
PARA_MAX_CHARS = 1200
PARA_OVERLAP_CHARS = 150

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SS_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _empty_result(status, error_class=None, fmt="unknown"):
    return {"format": fmt, "n_pages": 0, "n_text_pages": 0, "status": status,
            "error_class": error_class, "pages": [], "tables": []}


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #

def extract_pdf(path, pdftotext_exe, size_bytes, timeout_s=180):
    import pypdf
    try:
        reader = pypdf.PdfReader(str(path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
                n_pages = len(reader.pages)
            except Exception:
                return _empty_result("encrypted", "encrypted", "pdf")
        else:
            n_pages = len(reader.pages)
    except Exception as e:
        return _empty_result("parser_failed", type(e).__name__, "pdf")

    if n_pages == 0:
        return _empty_result("empty", None, "pdf")

    try:
        r = subprocess.run(
            [pdftotext_exe, "-layout", "-enc", "UTF-8", str(path), "-"],
            capture_output=True, timeout=timeout_s)
        full_text = r.stdout.decode("utf-8", errors="replace")
    except Exception as e:
        return _empty_result("parser_failed", type(e).__name__, "pdf")

    # pdftotext emits form-feed (\x0c) between physical pages; splitting on it
    # preserves physical page indices without renumbering empty pages.
    raw_pages = full_text.split("\x0c")
    if len(raw_pages) > n_pages:
        raw_pages = raw_pages[:n_pages]
    while len(raw_pages) < n_pages:
        raw_pages.append("")

    pages = []
    n_text_pages = 0
    tables = []
    for idx, ptext in enumerate(raw_pages):
        stripped = ptext.strip()
        if stripped:
            n_text_pages += 1
            status = "readable"
        else:
            status = "no_text"
        pages.append({"page_index": idx, "text_status": status, "raw_text": ptext})
        tables.extend(_detect_pdf_tables(ptext, idx))

    if n_text_pages == 0:
        overall = "no_text"
    elif n_text_pages < n_pages:
        overall = "partially_readable"
    else:
        overall = "readable"

    return {"format": "pdf", "n_pages": n_pages, "n_text_pages": n_text_pages,
            "status": overall, "error_class": None, "pages": pages, "tables": tables}


CAPTION_RE = re.compile(r"^\s*(Table|Exhibit)\s+([A-Za-z0-9\.\-]+)\s*[:\.]?\s*(.*)$")
YEAR_RE = re.compile(r"\b\d{4}-\d{2}\b")
NUM_CELL_RE = re.compile(r"-?\d[\d,]*\.?\d*\s*[PR]?\b")


def _detect_pdf_tables(page_text, page_index):
    """Two deterministic detectors per the contract: (a) a line-start numbered
    Table/Exhibit caption, capturing following lines up to the next caption,
    a source footer, or 60 lines; (b) an aligned block with >=2 year headers
    and >=2 numerical cells within 12 lines, for tables with no caption."""
    lines = page_text.splitlines()
    cards = []
    caption_line_idxs = []
    for i, line in enumerate(lines):
        m = CAPTION_RE.match(line)
        if m:
            caption_line_idxs.append((i, m))

    covered = set()
    for pos, (i, m) in enumerate(caption_line_idxs):
        end = i + 60
        if pos + 1 < len(caption_line_idxs):
            end = min(end, caption_line_idxs[pos + 1][0])
        body_lines = []
        for j in range(i + 1, min(end, len(lines))):
            if re.match(r"^\s*Source\s*:", lines[j], re.I):
                body_lines.append(lines[j])
                break
            body_lines.append(lines[j])
            covered.add(j)
        caption = "{} {}: {}".format(m.group(1), m.group(2), m.group(3)).strip()
        heading = _preceding_heading(lines, i)
        preceding_para = "\n".join(l for l in lines[max(0, i - 6):i] if l.strip())
        following_para = "\n".join(l for l in lines[min(end, len(lines)):min(end, len(lines)) + 6] if l.strip())
        card = _build_table_card_from_lines(caption, heading, body_lines, page_index,
                                             preceding_para=preceding_para,
                                             following_para=following_para)
        if card:
            cards.append(card)
        covered.add(i)

    # Captionless aligned blocks: >=2 year headers and >=2 numeric cells within
    # a 12-line window that is not already covered by a captioned card above.
    #
    # 2026-09-13 tuning loop: three tightened variants of this rule were
    # measured against the frozen 17-question dev set and a 30-question
    # holdout, trying to cut the 92.5% of the catalogue this loose rule
    # produces from ordinary prose (see the Stage-5 STOP_REASON.md addendum).
    # All three measured WORSE than this original rule on dev (3/17 -> 2/17
    # or 0/17), not better -- removing those "false positive" cards also
    # removed real retrieval surface (some questions' answers sit in
    # narrative prose sentences, not clean tables, and the compact
    # card-shaped version of that sentence out-competed the longer,
    # noisier paragraph_units() chunk containing the same sentence in the
    # separate prose channel). Reverted to this original rule; see
    # corpus-lab/state/evidence_v1/tuning_log.jsonl idea "1_captionless_detector"
    # iterations 1-3 for the measured numbers before concluding this was a
    # dead end for THIS idea, not evidence the loose rule is actually right.
    window = 12
    for start in range(0, max(0, len(lines) - 1), 1):
        if start in covered:
            continue
        chunk = lines[start:start + window]
        years = set()
        numeric_cells = 0
        for line in chunk:
            years |= set(YEAR_RE.findall(line))
            numeric_cells += len(NUM_CELL_RE.findall(line))
        if len(years) >= 2 and numeric_cells >= 2:
            heading = _preceding_heading(lines, start)
            card = _build_table_card_from_lines(None, heading, chunk, page_index,
                                                 kind_hint="uncaptioned")
            if card:
                cards.append(card)
            for k in range(start, start + window):
                covered.add(k)
            break  # one uncaptioned block per 12-line scan start is enough here
    return cards


def _preceding_heading(lines, idx):
    for j in range(idx - 1, max(-1, idx - 6), -1):
        s = lines[j].strip()
        if s and len(s) <= 160:
            return s
    return None


def _build_table_card_from_lines(caption, heading, body_lines, page_index, kind_hint=None,
                                  preceding_para="", following_para=""):
    body = "\n".join(body_lines).strip()
    if not body and not caption:
        return None
    source_m = re.search(r"Source\s*:\s*(.+)", body, re.I)
    unit_m = re.search(r"Unit\s*:\s*([^\|]+)", body, re.I)
    years = YEAR_RE.findall((caption or "") + " " + body)
    row_label = None
    for line in body_lines:
        s = line.strip()
        if s and not re.match(r"^(Indicator|Unit\s*:|Source\s*:)", s, re.I):
            row_label = s[:160]
            break
    search_text_a = " | ".join(x for x in [caption, heading, row_label,
                                            "cols:" + ",".join(sorted(set(years)))] if x)
    search_text_b = " | ".join(x for x in [search_text_a, preceding_para, following_para] if x)
    full_text = "\n".join(x for x in [caption, heading, body] if x)
    return {
        "page_index": page_index, "kind": "table" if caption else (kind_hint or "table"),
        "caption": caption, "heading": heading, "row_labels": [row_label] if row_label else [],
        "col_headers": sorted(set(years)),
        "unit_literal": unit_m.group(1).strip() if unit_m else None,
        "source_literal": source_m.group(1).strip() if source_m else None,
        "search_text": search_text_a[:1500], "search_text_b": search_text_b[:2400],
        "full_text": full_text, "truncated": len(search_text_a) > 1500,
    }


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #

def extract_csv(path, size_bytes):
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
            rows = list(csv.reader(f))
    except Exception as e:
        return _empty_result("parser_failed", type(e).__name__, "csv")
    if not rows:
        return _empty_result("empty", None, "csv")
    header = rows[0]
    search_text = "columns: " + ", ".join(header)
    full_text = "\n".join(",".join(r) for r in rows[:200])
    card = {
        "page_index": None, "kind": "table", "caption": None, "heading": None,
        "row_labels": [r[0] for r in rows[1:50] if r], "col_headers": header,
        "unit_literal": None, "source_literal": None,
        "search_text": search_text[:1500], "full_text": full_text,
        "truncated": len(rows) > 200,
    }
    page_text = "\n".join(",".join(r) for r in rows)
    return {"format": "csv", "n_pages": 1, "n_text_pages": 1, "status": "readable",
            "error_class": None,
            "pages": [{"page_index": 0, "text_status": "readable", "raw_text": page_text}],
            "tables": [card]}


# --------------------------------------------------------------------------- #
# DOCX (stdlib zip + XML; python-docx is not an allowed/installed dependency)
# --------------------------------------------------------------------------- #

def extract_docx(path, size_bytes):
    try:
        with zipfile.ZipFile(path) as z:
            xml_bytes = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as e:
        return _empty_result("parser_failed", type(e).__name__, "docx")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return _empty_result("parser_failed", type(e).__name__, "docx")

    body_text_parts = []
    for p in root.iter(W_NS + "p"):
        texts = [t.text or "" for t in p.iter(W_NS + "t")]
        if texts:
            body_text_parts.append("".join(texts))
    full_page_text = "\n".join(body_text_parts)

    tables = []
    for t_ordinal, tbl in enumerate(root.iter(W_NS + "tbl")):
        rows = []
        for tr in tbl.findall("./" + W_NS + "tr"):
            cells = []
            for tc in tr.findall("./" + W_NS + "tc"):
                texts = [t.text or "" for t in tc.iter(W_NS + "t")]
                cells.append("".join(texts))
            rows.append(cells)
        if not rows:
            continue
        header = rows[0]
        search_text = "table {} columns: {}".format(t_ordinal + 1, ", ".join(header))
        tables.append({
            "page_index": 0, "kind": "table", "caption": None, "heading": None,
            "row_labels": [r[0] for r in rows[1:] if r], "col_headers": header,
            "unit_literal": None, "source_literal": None,
            "search_text": search_text[:1500],
            "full_text": "\n".join(" | ".join(r) for r in rows),
            "truncated": False, "table_ordinal": t_ordinal + 1,
        })

    status = "readable" if (full_page_text.strip() or tables) else "no_text"
    return {"format": "docx", "n_pages": 1, "n_text_pages": 1 if status == "readable" else 0,
            "status": status, "error_class": None,
            "pages": [{"page_index": 0, "text_status": status, "raw_text": full_page_text}],
            "tables": tables}


# --------------------------------------------------------------------------- #
# XLSX (stdlib zip + XML; openpyxl is not an allowed/installed dependency)
# --------------------------------------------------------------------------- #

def _col_letter_to_index(letters):
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx - 1


def extract_xlsx(path, size_bytes):
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        return _empty_result("parser_failed", type(e).__name__, "xlsx")
    try:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            sroot = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sroot.findall(SS_NS + "si"):
                texts = [t.text or "" for t in si.iter(SS_NS + "t")]
                shared.append("".join(texts))

        sheet_names = []
        wb_root = ET.fromstring(z.read("xl/workbook.xml"))
        for sheet in wb_root.iter(SS_NS + "sheet"):
            sheet_names.append(sheet.get("name"))

        sheet_files = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n))
    except (KeyError, ET.ParseError) as e:
        return _empty_result("parser_failed", type(e).__name__, "xlsx")

    tables = []
    any_rows = False
    for sidx, sfile in enumerate(sheet_files):
        try:
            sroot = ET.fromstring(z.read(sfile))
        except ET.ParseError:
            continue
        rows_out = []
        for row in sroot.iter(SS_NS + "row"):
            cells = {}
            max_col = -1
            for c in row.findall(SS_NS + "c"):
                ref = c.get("r", "")
                col_letters = re.match(r"[A-Z]+", ref)
                col_idx = _col_letter_to_index(col_letters.group()) if col_letters else len(cells)
                ctype = c.get("t")
                v_el = c.find(SS_NS + "v")
                if v_el is None:
                    is_el = c.find(SS_NS + "is")
                    val = "".join(t.text or "" for t in is_el.iter(SS_NS + "t")) if is_el is not None else ""
                elif ctype == "s":
                    si = int(v_el.text)
                    val = shared[si] if si < len(shared) else ""
                else:
                    val = v_el.text
                cells[col_idx] = val
                max_col = max(max_col, col_idx)
            rows_out.append([cells.get(i, "") for i in range(max_col + 1)])
        if not rows_out:
            continue
        any_rows = True
        header = rows_out[0]
        name = sheet_names[sidx] if sidx < len(sheet_names) else "Sheet{}".format(sidx + 1)
        tables.append({
            "page_index": sidx, "kind": "table", "caption": None,
            "heading": "Sheet: {}".format(name),
            "row_labels": [r[0] for r in rows_out[1:] if r], "col_headers": header,
            "unit_literal": None, "source_literal": None,
            "search_text": "sheet {} columns: {}".format(name, ", ".join(str(h) for h in header))[:1500],
            "full_text": "\n".join(",".join(str(c) for c in r) for r in rows_out[:500]),
            "truncated": len(rows_out) > 500, "sheet_name": name,
        })

    status = "readable" if any_rows else "no_text"
    pages = [{"page_index": i, "text_status": "readable", "raw_text": t["full_text"]}
             for i, t in enumerate(tables)]
    return {"format": "xlsx", "n_pages": max(1, len(tables)), "n_text_pages": len(tables),
            "status": status, "error_class": None, "pages": pages, "tables": tables}


# --------------------------------------------------------------------------- #
# Plain text / markdown / logs -- text units only, no table cards
# --------------------------------------------------------------------------- #

def extract_text(path, size_bytes):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return _empty_result("parser_failed", type(e).__name__, "text")
    if not text.strip():
        return _empty_result("empty", None, "text")
    return {"format": "text", "n_pages": 1, "n_text_pages": 1, "status": "readable",
            "error_class": None,
            "pages": [{"page_index": 0, "text_status": "readable", "raw_text": text}],
            "tables": []}


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf", ".csv": "csv", ".docx": "docx", ".xlsx": "xlsx",
    ".md": "text", ".txt": "text", ".log": "text",
}


def extract(path, ext, pdftotext_exe, size_bytes):
    fmt = SUPPORTED_EXTENSIONS.get(ext.lower())
    if fmt is None:
        return _empty_result("unsupported", "unsupported_extension", ext.lstrip("."))
    if fmt == "pdf":
        return extract_pdf(path, pdftotext_exe, size_bytes)
    if fmt == "csv":
        return extract_csv(path, size_bytes)
    if fmt == "docx":
        return extract_docx(path, size_bytes)
    if fmt == "xlsx":
        return extract_xlsx(path, size_bytes)
    return extract_text(path, size_bytes)


def text_units(raw_text, unit_lines=TEXT_UNIT_LINES, overlap=TEXT_UNIT_OVERLAP):
    """80-line units, 10-line overlap, original line numbers retained."""
    lines = raw_text.splitlines()
    if not lines:
        return []
    units = []
    start = 0
    step = max(1, unit_lines - overlap)
    while start < len(lines):
        end = min(start + unit_lines, len(lines))
        units.append({"first_line": start, "last_line": end - 1,
                       "text": "\n".join(lines[start:end])})
        if end == len(lines):
            break
        start += step
    return units


def paragraph_units(raw_text, max_chars=PARA_MAX_CHARS, overlap=PARA_OVERLAP_CHARS):
    """PDF prose units: paragraphs, max 1200 chars, 150-char overlap, within a
    physical page. A 'paragraph' is a run of non-blank lines."""
    paras = re.split(r"\n\s*\n", raw_text)
    units = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_chars:
            units.append(p)
        else:
            start = 0
            step = max(1, max_chars - overlap)
            while start < len(p):
                units.append(p[start:start + max_chars])
                if start + max_chars >= len(p):
                    break
                start += step
    return units
