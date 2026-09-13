#!/usr/bin/env python
"""evidence_v1.compile -- the answer compiler.

Runtime code, no labpaths import. Accepts only evidence records already
issued to THIS request (by evidence_v1.cli's `read` command, which verified
them via evidence_v1.verify against the live, current-hash source). Never
accepts a model-supplied numeric value, SQL, or arbitrary Python. Decimal
arithmetic only; whitelisted conversions only.

Outcome enum: ANSWER, PARTIAL, CONFLICT, NOT_FOUND_IN_SEARCHED_MATERIAL,
UNAVAILABLE_COVERAGE, AMBIGUOUS_EXTRACTION, INDEX_PENDING, ENGINE_ERROR.
"""
from decimal import Decimal, InvalidOperation

MAX_ANSWER_WORDS = 700

REFUSAL_TEMPLATE = (
    "I found no supporting evidence for this request in the material I could "
    "search. Searched: {files} files, {pages} readable pages. Not searched: "
    "{unavailable} files and {pending} pending changes. This does not "
    "establish absence from unreadable material. Evidence receipt: {request_id}")

CANDIDATE_CAP_NOTE = "Candidate review was capped at {n}; this search was not exhaustive."


def _norm_unit(u):
    return (u or "").strip().lower()


UNIT_CONVERSIONS = {
    ("rs million", "rs billion"): Decimal("0.001"),
    ("rs billion", "rs million"): Decimal("1000"),
}


def _to_decimal(raw_value):
    if raw_value is None:
        return None
    try:
        cleaned = str(raw_value).replace(",", "").strip()
        flag = None
        if cleaned.endswith(("P", "R")):
            flag = cleaned[-1]
            cleaned = cleaned[:-1].strip()
        return Decimal(cleaned), flag
    except InvalidOperation:
        return None, None


def cite(ev):
    """'[relative path; PDF p.N; printed label; table]' or structural address."""
    if ev.get("format") == "pdf":
        return "[{}; PDF p.{}; {}; {}]".format(
            ev.get("current_path"), ev.get("viewer_page"),
            ev.get("printed_label") or ev.get("column_label") or "",
            ev.get("table_label") or "")
    if ev.get("format") == "csv":
        return "[{}; row {!r}; column {!r}]".format(
            ev.get("current_path"), ev.get("row_label"), ev.get("column_label"))
    if ev.get("format") == "docx":
        return "[{}; table {}; row {!r}; column {!r}]".format(
            ev.get("current_path"), ev.get("table_id"), ev.get("row_label"),
            ev.get("column_label"))
    if ev.get("format") == "xlsx":
        return "[{}; sheet {}; cell]".format(ev.get("current_path"), ev.get("table_label"))
    return "[{}]".format(ev.get("current_path"))


def _footer(request_id):
    return "Evidence receipt: {}".format(request_id)


def op_quote(evidence, request_id):
    if not evidence:
        return {"outcome": "NOT_FOUND_IN_SEARCHED_MATERIAL", "answer_text": None}
    ev = evidence[0]
    text = "{}\n\n{}\n{}".format(ev.get("quote", ""), cite(ev), _footer(request_id))
    return {"outcome": "ANSWER", "answer_text": text, "claims": [ev]}


def op_table(evidence, request_id):
    if not evidence:
        return {"outcome": "NOT_FOUND_IN_SEARCHED_MATERIAL", "answer_text": None}
    lines = []
    claims = []
    for ev in evidence:
        if ev.get("verification_status") != "verified":
            continue
        val, flag = _to_decimal(ev.get("raw_value"))
        if val is None:
            continue
        flagtxt = " ({})".format(ev["status_literal"]) if ev.get("status_literal") else ""
        lines.append("{}: {} {}{} -- {}".format(
            ev.get("period_literal") or ev.get("column_label"), val,
            ev.get("unit_literal") or "", flagtxt, cite(ev)))
        claims.append(ev)
    if not lines:
        return {"outcome": "AMBIGUOUS_EXTRACTION", "answer_text": None}
    text = "\n".join(lines) + "\n\n" + _footer(request_id)
    outcome = "ANSWER" if len(lines) == len(evidence) else "PARTIAL"
    return {"outcome": outcome, "answer_text": text, "claims": claims}


def op_trajectory(evidence, request_id):
    """Four-source trajectories use >=4 distinct nonidentical documents when
    available, otherwise disclose the actual count. A label-literal change
    across the series must be surfaced, never silently smoothed over."""
    verified = [e for e in evidence if e.get("verification_status") == "verified"]
    if not verified:
        return {"outcome": "AMBIGUOUS_EXTRACTION", "answer_text": None}
    distinct_sources = {e["source_sha256"] for e in verified}
    labels = {e.get("row_label") for e in verified if e.get("row_label")}
    by_period = sorted(verified, key=lambda e: e.get("period_literal") or "")
    lines = []
    for e in by_period:
        val, _ = _to_decimal(e.get("raw_value"))
        flagtxt = " ({})".format(e["status_literal"]) if e.get("status_literal") else ""
        lines.append("{}: {} {}{} -- {}".format(
            e.get("period_literal"), val, e.get("unit_literal") or "", flagtxt, cite(e)))
    header = []
    if len(labels) > 1:
        header.append(
            "NOTE: the printed row label changes across this series ({}); a single "
            "smooth number across the whole span is not established without an "
            "explicit bridge.".format(" -> ".join(sorted(labels))))
    header.append("Distinct source documents used: {} of {} addresses.".format(
        len(distinct_sources), len(verified)))
    text = "\n".join(header) + "\n\n" + "\n".join(lines) + "\n\n" + _footer(request_id)
    outcome = "PARTIAL" if len(labels) > 1 else "ANSWER"
    return {"outcome": outcome, "answer_text": text, "claims": verified,
            "n_distinct_sources": len(distinct_sources)}


def op_compare(evidence, request_id):
    verified = [e for e in evidence if e.get("verification_status") == "verified"]
    if len(verified) < 2:
        return {"outcome": "UNAVAILABLE_COVERAGE", "answer_text": None}
    a, b = verified[0], verified[1]
    ua, ub = _norm_unit(a.get("unit_literal")), _norm_unit(b.get("unit_literal"))
    va, _ = _to_decimal(a.get("raw_value"))
    vb, _ = _to_decimal(b.get("raw_value"))
    if va is None or vb is None:
        return {"outcome": "AMBIGUOUS_EXTRACTION", "answer_text": None}
    if ua != ub:
        factor = UNIT_CONVERSIONS.get((ua, ub))
        if factor is None:
            return {"outcome": "CONFLICT", "answer_text":
                     "Units differ ({!r} vs {!r}) with no whitelisted conversion; "
                     "not compared.\n\n{}".format(a.get("unit_literal"), b.get("unit_literal"),
                                                   _footer(request_id)),
                     "claims": verified}
        vb = vb * factor
    diff = va - vb
    pct = (diff / vb * 100) if vb != 0 else None
    direction = "rose" if diff > 0 else ("fell" if diff < 0 else "unchanged")
    text = ("{} {} from {} to {} ({} percentage points{}).\n\n{}\n{}\n\n{}").format(
        a.get("row_label") or "value", direction, vb, va, diff,
        "" if pct is None else ", {:.1f}%".format(pct), cite(a), cite(b),
        _footer(request_id))
    return {"outcome": "ANSWER", "answer_text": text, "claims": verified}


def op_mean_compare(evidence, request_id, requested_years=None):
    """Splits an EXPLICITLY supplied 10-year interval into first five/last
    five; requires 10/10 matching observations; unspecified decade is an
    ambiguity outcome, not an invented interval."""
    if not requested_years or len(requested_years) != 10:
        return {"outcome": "AMBIGUOUS_EXTRACTION", "answer_text":
                 "A mean-compare over a decade requires an explicitly supplied "
                 "10-year interval; none was given."}
    verified = {e.get("period_literal"): e for e in evidence
                if e.get("verification_status") == "verified"}
    have = [y for y in requested_years if y in verified]
    if len(have) != 10:
        return {"outcome": "UNAVAILABLE_COVERAGE", "answer_text":
                 "Only {}/10 requested years have a verified observation; a "
                 "missing year cannot silently reduce the denominator.".format(len(have))}
    vals = [_to_decimal(verified[y].get("raw_value"))[0] for y in requested_years]
    first5 = vals[:5]
    last5 = vals[5:]
    mean1 = sum(first5) / Decimal(5)
    mean2 = sum(last5) / Decimal(5)
    text = ("First five years mean: {} ({}/5 observations)\nLast five years mean: "
            "{} ({}/5 observations)\n\n{}").format(mean1, 5, mean2, 5, _footer(request_id))
    return {"outcome": "ANSWER", "answer_text": text, "claims": list(verified.values())}


def op_not_found(request_id, counts):
    text = REFUSAL_TEMPLATE.format(
        files=counts.get("files", 0), pages=counts.get("pages", 0),
        unavailable=counts.get("unavailable", 0), pending=counts.get("pending", 0),
        request_id=request_id)
    if counts.get("candidate_cap_hit"):
        text = text.replace(_footer(request_id),
                             CANDIDATE_CAP_NOTE.format(n=counts["candidate_cap_hit"]) +
                             " " + _footer(request_id))
    return {"outcome": "NOT_FOUND_IN_SEARCHED_MATERIAL", "answer_text": text, "claims": []}


def check_compatibility(ev, requested):
    """Derived from evidence fields only -- never a free-text equivalence
    declaration. Returns (ok, reason). `requested` carries any of
    period_literal, unit_literal, geography_literal, population_literal,
    status_literal (allocation vs execution is carried as status_literal/
    source_literal text, e.g. 'allocation' vs 'execution'/'released').
    """
    if requested.get("period_literal") and ev.get("period_literal") and \
            requested["period_literal"] != ev["period_literal"]:
        return False, "wrong_year: requested {!r}, evidence is {!r}".format(
            requested["period_literal"], ev["period_literal"])
    if requested.get("unit_literal") and ev.get("unit_literal") and \
            _norm_unit(requested["unit_literal"]) != _norm_unit(ev["unit_literal"]) and \
            (_norm_unit(ev["unit_literal"]), _norm_unit(requested["unit_literal"])) not in UNIT_CONVERSIONS:
        return False, "wrong_unit: requested {!r}, evidence is {!r}".format(
            requested["unit_literal"], ev["unit_literal"])
    if requested.get("series_kind") and ev.get("series_kind") and \
            requested["series_kind"] != ev["series_kind"]:
        return False, "allocation_vs_execution: requested {!r}, evidence is {!r}".format(
            requested["series_kind"], ev["series_kind"])
    if requested.get("population_literal") and ev.get("population_literal") and \
            requested["population_literal"] != ev["population_literal"]:
        return False, "population_mismatch: requested {!r}, evidence is {!r}".format(
            requested["population_literal"], ev["population_literal"])
    if requested.get("row_label") and ev.get("row_label") and \
            requested["row_label"] != ev["row_label"] and not requested.get("label_bridge"):
        return False, "changed_label_without_bridge: requested {!r}, evidence row is {!r}".format(
            requested["row_label"], ev["row_label"])
    if ev.get("evidence_id") and requested.get("issued_evidence_ids") is not None and \
            ev["evidence_id"] not in requested["issued_evidence_ids"]:
        return False, "forged_evidence_id: {!r} was never issued to this request".format(
            ev["evidence_id"])
    if ev.get("source_sha256") and ev.get("current_hash_at_read") and \
            ev["source_sha256"] != ev["current_hash_at_read"]:
        return False, "stale_hash: source changed since this evidence was read"
    return True, None


OPERATIONS = {
    "table": op_table, "trajectory": op_trajectory, "compare": op_compare,
    "mean_compare": op_mean_compare, "quote": op_quote,
}


def compose(operation, evidence, request_id, requested=None, **kwargs):
    if operation == "not_found":
        return op_not_found(request_id, kwargs.get("counts", {}))
    fn = OPERATIONS.get(operation)
    if fn is None:
        return {"outcome": "ENGINE_ERROR", "answer_text": "unknown operation: {}".format(operation)}

    rejected = []
    accepted = evidence
    if requested is not None:
        accepted, rejected = [], []
        for ev in evidence:
            ok, reason = check_compatibility(ev, requested)
            (accepted if ok else rejected).append(ev if ok else (ev, reason))
        if rejected and not accepted:
            reasons = "; ".join(r for _, r in rejected)
            return {"outcome": "CONFLICT", "answer_text":
                     "Every supplied evidence item failed a compatibility check: {}\n\n{}"
                     .format(reasons, _footer(request_id)),
                     "claims": [], "rejected": rejected}

    result = fn(accepted, request_id, **({k: v for k, v in kwargs.items() if k in
                                           ("requested_years",)} if operation == "mean_compare" else {}))
    if rejected:
        result["rejected"] = rejected
    text = result.get("answer_text")
    if text and len(text.split()) > MAX_ANSWER_WORDS:
        words = text.split()
        text = " ".join(words[:MAX_ANSWER_WORDS]) + "\n\n" + _footer(request_id)
        result["answer_text"] = text
        result["truncated_to_word_limit"] = True
    return result
