"""Bounded, read-only checks of supplied data; not an external-truth/runtime oracle."""
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation, localcontext

MAX_TEXT = 100_000
NUMBERS = {
    "en": re.compile(r"(?<![\w])[-+]?(?:\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?:\.\d+)?"),
    "vi": re.compile(r"(?<![\w])[-+]?(?:\d{1,3}(?:\.\d{3})+(?!\d)|\d+)(?:,\d+)?"),
}
CANONICAL = re.compile(r"[-+]?\d{1,50}(?:\.\d{1,50})?\Z")
SCOPE = "Supplied inputs only. Not source authentication, semantic review, test execution or publish approval."
HINT = ("\n\nDeterministic verification: Before claiming a deliverable/AC passes or stating a self-computed "
        "word/character count or numeric total, call verify_facts on the EXACT final draft. "
        "Use texts for counts/limits (blog body only, no title/SEO); sums for Rubric/status distributions; "
        "number_checks with exact source/draft quotes for numeric facts; checklist references computed check ids. "
        "Copy returned numbers, never mental estimates. FAIL means an assertion failed, not that computed counts/totals are unknown: correct the draft using the computed value. Any later edit requires rechecking. "
        "Manual runtime ACs remain NOT_CHECKED; PASS here is not tests/render/source verification. "
        "A one-step spelling answer with no count/PASS claim needs no verification ceremony.")


def _text(value):
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        raise ValueError("Text must be a string of at most 100000 Unicode code points")
    return value


def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)) or not CANONICAL.fullmatch(str(value)):
        raise ValueError("Use finite canonical decimals without grouping/exponents, e.g. 650000 or 0.5")
    return Decimal(str(value))


def _display(value):
    return format(value, "f")


def _numbers(text, fmt):
    result = set()
    for match in NUMBERS[fmt].finditer(text):
        token = match.group()
        token = token.replace(".", "").replace(",", ".") if fmt == "vi" else token.replace(",", "")
        try:
            result.add(_decimal(token))
        except ValueError:
            pass
    return result


def verify(args):
    """No eval/files/network/writes. AC PASS can only derive from computed checks."""
    try:
        if not isinstance(args, dict):
            raise ValueError("Arguments must be an object")
        draft, source = _text(args.get("draft", "")), _text(args.get("source", ""))
        fmt = args.get("number_format", "en")
        source_fmt, draft_fmt = args.get("source_number_format", fmt), args.get("draft_number_format", fmt)
        if any(f not in ("en", "vi") for f in (fmt, source_fmt, draft_fmt)):
            raise ValueError("number_format must be en or vi (quotes only; numeric inputs canonical)")
        groups = {key: args.get(key, []) for key in ("texts", "sums", "number_checks", "diffs", "checklist")}
        if any(not isinstance(v, list) or len(v) > 50 for v in groups.values()):
            raise ValueError("Each group needs an array of at most 50 items")
        checks, ids = [], set()

        def identify(item):
            if not isinstance(item, dict):
                raise ValueError("Each check must be an object")
            ident = item.get("id")
            if not isinstance(ident, str) or not ident or len(ident) > 80 or ident in ids:
                raise ValueError("Check ids must be nonempty, unique and at most 80 characters")
            ids.add(ident)
            return ident

        for item in groups["texts"]:
            ident, text = identify(item), _text(item.get("text"))
            counts = {"words": len(text.split()), "chars": len(text),
                      "chars_without_whitespace": sum(not c.isspace() for c in text)}
            failed = []
            for key in ("words", "chars"):
                lo, hi, claimed = (item.get(p + key) for p in ("min_", "max_", "claimed_"))
                if any(v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 0) for v in (lo, hi, claimed)):
                    raise ValueError("Counts/limits must be nonnegative integers")
                if lo is not None and hi is not None and lo > hi:
                    raise ValueError("Minimum exceeds maximum")
                if (lo is not None and counts[key] < lo) or (hi is not None and counts[key] > hi):
                    failed.append(key + "_limit")
                if claimed is not None and counts[key] != claimed:
                    failed.append("claimed_" + key)
            checks.append({"id": ident, "kind": "text", "status": "FAIL" if failed else "PASS", **counts,
                           "failed": failed, "sha256": hashlib.sha256(text.encode()).hexdigest()})
        with localcontext() as ctx:
            ctx.prec = 128
            for item in groups["sums"]:
                ident, values = identify(item), item.get("values")
                if not isinstance(values, list) or not values or len(values) > 100:
                    raise ValueError("A sum needs 1–100 canonical decimal values")
                total = sum((_decimal(v) for v in values), Decimal(0))
                claimed = item.get("claimed_total")
                matches = claimed is None or total == _decimal(claimed)
                checks.append({"id": ident, "kind": "sum", "total": _display(total),
                               "claimed_total_matches": matches if claimed is not None else None,
                               "status": "PASS" if matches else "FAIL"})
        for item in groups["number_checks"]:
            ident = identify(item)
            expected, actual = _decimal(item.get("expected")), _decimal(item.get("actual"))
            sq, dq = _text(item.get("source_quote", "")), _text(item.get("draft_quote", ""))
            sf, df = bool(sq) and sq in source, bool(dq) and dq in draft
            grounded = sf and df and expected in _numbers(sq, source_fmt) and actual in _numbers(dq, draft_fmt)
            checks.append({"id": ident, "kind": "number", "status": "FAIL" if expected != actual else "PASS" if grounded else "NOT_CHECKED",
                           "expected": _display(expected), "actual": _display(actual),
                           "source_quote_found": sf, "draft_quote_found": df, "numeric_quotes_grounded": grounded})
        for item in groups["diffs"]:
            ident, text = identify(item), _text(item.get("text"))
            lines, hunks = text.splitlines(), []
            for i, line in enumerate(lines):
                match = re.fullmatch(r"@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@.*", line)
                if not match:
                    continue
                old, new = 0, 0
                for body in lines[i+1:]:
                    if body.startswith("\\ No newline"):
                        continue
                    if not body or body.startswith(("@@", "--- ", "+++ ")) or body[0] not in " +-":
                        break
                    old += body[0] in " -"
                    new += body[0] in " +"
                expected_old, expected_new = (int(v) if v is not None else 1 for v in match.groups())
                hunks.append({"header_old": expected_old, "actual_old": old,
                              "header_new": expected_new, "actual_new": new,
                              "status": "PASS" if (old,new)==(expected_old,expected_new) else "FAIL"})
            status = "FAIL" if any(h["status"]=="FAIL" for h in hunks) else "PASS" if hunks else "NOT_CHECKED"
            checks.append({"id": ident, "kind": "diff_hunks", "status": status, "hunks": hunks,
                           "scope": "Hunk line counts only, NOT context/apply/test validation"})
        known = {c["id"]: c["status"] for c in checks}
        checklist = []
        for item in groups["checklist"]:
            ident, refs = identify(item), item.get("check_ids", [])
            if not isinstance(refs, list) or len(refs) > 50 or any(not isinstance(r, str) for r in refs):
                raise ValueError("check_ids must be an array of strings")
            states = [known.get(r, "NOT_CHECKED") for r in refs]
            status = "FAIL" if "FAIL" in states else "PASS" if states and all(s == "PASS" for s in states) else "NOT_CHECKED"
            checklist.append({"id": ident, "status": status, "check_ids": refs, "unknown_check_ids": [r for r in refs if r not in known]})
        states = [c["status"] for c in checks + checklist]
        overall = "FAIL" if "FAIL" in states else "PASS" if states and all(s == "PASS" for s in states) else "NOT_CHECKED"
        result = {"scope": SCOPE, "count_method": "words=str.split whitespace tokens (VI: not linguistic words); chars=Unicode code points, no normalization",
                  "calculation_status": "COMPLETE", "interpretation": "Computed values are authoritative for supplied inputs. FAIL means a claim/limit failed: correct the draft, not the computed value.",
                  "draft_sha256": hashlib.sha256(draft.encode()).hexdigest(), "checks": checks, "checklist": checklist, "overall": overall}
        if draft and source:
            extra = sorted(_numbers(draft, draft_fmt) - _numbers(source, source_fmt))
            result["numeric_inventory"] = {"draft_numbers_not_in_source": [_display(x) for x in extra[:100]], "truncated": len(extra) > 100,
                "note": "Informational: structural ids/derived numbers may be legitimate; value presence does not verify entity/unit/meaning."}
        return result
    except (ValueError, TypeError, InvalidOperation) as e:
        return {"error": str(e), "overall": "NOT_CHECKED", "scope": SCOPE}


def tool(args):
    out = json.dumps(verify(args), ensure_ascii=False)
    if len(out) > 7500:
        return json.dumps({"error": "Result exceeds safe tool budget; split checks into smaller batches", "overall": "NOT_CHECKED", "scope": SCOPE})
    return out


STR = {"type": "string"}
NUM = {"type": ["number", "string"]}
COUNT = {"type": "integer", "minimum": 0}


def _items(properties, required):
    return {"type": "array", "maxItems": 50, "items": {"type": "object", "properties": properties, "required": required}}


SCHEMA = {"type": "function", "function": {"name": "verify_facts",
    "description": "Deterministically check exact final draft counts/limits, sums, source numeric quotes and AC references. No shell/LLM. Copy returned counts/totals; recheck after edits. PASS applies only to supplied checks, not runtime or external truth.",
    "parameters": {"type": "object", "properties": {
        "draft": {"type": "string", "description": "Exact final deliverable, excluding appended verification note."},
        "source": {"type": "string", "description": "Supplied source text/table, not invented evidence."},
        "number_format": {"type": "string", "enum": ["en", "vi"], "description": "Quote numbers: en 650,000.5 or vi 650.000,5. JSON numeric values always canonical."},
        "source_number_format": {"type": "string", "enum": ["en", "vi"]},
        "draft_number_format": {"type": "string", "enum": ["en", "vi"]},
        "texts": _items({"id": STR, "text": {"type": "string", "description": "Exact section to count; blog BODY ONLY, omit heading/SEO."},
                         **{k: COUNT for k in ("min_words", "max_words", "min_chars", "max_chars", "claimed_words", "claimed_chars")}}, ["id", "text"]),
        "sums": _items({"id": STR, "values": {"type": "array", "items": NUM}, "claimed_total": NUM}, ["id", "values"]),
        "number_checks": _items({"id": STR, "expected": NUM, "actual": NUM, "source_quote": STR, "draft_quote": STR}, ["id", "expected", "actual", "source_quote", "draft_quote"]),
        "diffs": _items({"id": STR, "text": {"type": "string", "description": "Exact unified diff. Compute actual hunk counts from lines, not a self-reported sum. Does not apply or run code."}}, ["id", "text"]),
        "checklist": _items({"id": STR, "check_ids": {"type": "array", "items": STR, "description": "References computed check ids above. Empty/missing/manual refs stay NOT_CHECKED; cannot declare PASS."}}, ["id", "check_ids"])
    }}}}
