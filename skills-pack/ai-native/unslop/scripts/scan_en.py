#!/usr/bin/env python3
"""Scanner for AI tells and Vietnamese-transfer errors in English (unslop).

Flags candidates by the rule ids in SKILL.md. Every flag still needs judgment
in context; the scanner does not understand meaning.

Usage:
    python3 scan_en.py post.md
    python3 scan_en.py -                          # stdin
    python3 scan_en.py --json post.md
    python3 scan_en.py --keyword "slow website" post.md
    python3 scan_en.py --compare draft.md final.md
"""
import argparse
import json
import re
import statistics
import sys
import unicodedata
from collections import defaultdict

F = re.IGNORECASE


def alt(words):
    return r"\b(?:" + "|".join(words) + r")\b"


PATTERNS = [
    # Content
    ("3", r",\s+(?:highlighting|emphasizing|emphasising|showcasing|reflecting|ensuring|fostering|underscoring|contributing to|paving the way|cementing|solidifying)\b", "-ing tail"),
    ("5", r"\b(?:experts?|analysts|researchers|scientists|critics)\s+(?:say|believe|agree|suggest|argue|predict|note)\b", "vague attribution"),
    ("5", r"\b(?:studies|research|surveys|data|reports)\s+(?:show|shows|suggest|suggests|have shown|has shown|indicate|indicates|prove)\b", "vague attribution (name it)"),
    ("5", r"\b(?:it is|it's) (?:widely|generally|commonly) (?:believed|accepted|known|agreed)\b|\bmany (?:people|experts) (?:say|believe|think)\b|\bindustry reports\b", "vague attribution"),
    # Language
    ("7", alt(["additionally", "furthermore", "moreover", "crucial", "pivotal", "delve", "delves", "delving", "enhance", "enhances", "enhancing", "elevate", "elevates", "foster", "fosters", "fostering", "garner", "interplay", "intricate", "landscape", "realm", "showcase", "showcases", "tapestry", "testament", "underscore", "underscores", "vibrant", "robust", "seamless", "seamlessly", "comprehensive", "holistic", "cutting-edge", "state-of-the-art", "groundbreaking", "revolutionary", "revolutionize", "streamline", "empower", "empowers", "unlock", "unlocks", "harness", "leverage", "leverages", "leveraging", "embark", "meticulous", "meticulously", "paramount", "myriad", "plethora", "bespoke", "synergy", "game-changer", "game-changing", "ever-evolving", "ever-changing", "nuanced", "navigate", "navigating"]), "AI vocabulary"),
    ("7", r"\bplays? an? (?:crucial|pivotal|key|vital|important|significant) role\b|\bin today's (?:fast-paced|digital|ever-changing|modern) (?:world|landscape|age|era)\b|\b(?:a )?deep dive\b|\bthe power of\b|\bto the next level\b|\bstands? out as\b|\blook no further\b|\bwhether you're an? \w+ or an?\b|\bit's no secret\b|\bfull potential\b", "AI phrase"),
    ("8", r"\b(?:serves? as|stands? as|boasts?|is home to|comes equipped with)\b", "fancy 'is/has'"),
    ("9", r"\bnot (?:just|only|merely|simply)\b[^.!?\n]{1,80}\bbut\b|\b(?:it's|it is) not (?:just )?(?:about )?[^.!?\n]{1,50}[,;.]\s*it's\b|\bisn't about\b[^.!?\n]{1,60}[.]\s*it's about\b|\bmore than just\b", "'not just X, but Y'"),
    ("12", r"\bfrom \w+(?: \w+){0,2} to \w+(?: \w+){0,2}, from\b", "false range"),
    # Style
    ("13", r"—|\s–\s|\s--\s", "em dash"),
    # Communication
    ("20", r"\b(?:I hope this helps|let me know if|feel free to|happy (?:coding|reading)|let's dive in|let's explore|let's take a look|buckle up|without further ado|of course!|certainly!|absolutely!)", "chatbot phrase"),
    ("22", r"\b(?:great question|you're absolutely right|what a great)\b", "sycophancy"),
    # Filler
    ("23", r"\b(?:in order to|due to the fact that|at this point in time|it is important to note|it's important to note|it's worth (?:noting|mentioning)|it is worth (?:noting|mentioning)|when it comes to|in terms of|the fact that|a number of)\b", "filler"),
    ("24", r"\b(?:could potentially|may possibly|might possibly|it could be argued|to some extent|in some ways|arguably)\b", "hedging"),
    ("25", r"\b(?:in conclusion|to sum up|in summary|to summarize|ultimately,|at the end of the day|the future (?:looks|is) bright|the possibilities are endless|only time will tell|stay tuned)\b", "generic ending"),
    # Jargon
    ("26", alt(["north star", "flywheel", "moat", "bedrock", "cornerstone", "linchpin", "secret sauce", "silver bullet", "low-hanging fruit", "double-edged sword", "paradigm", "ecosystem", "journey", "building blocks", "uncharted waters"]), "metaphor noun"),
    # Plain speech
    ("30", alt(["really", "truly", "incredibly", "extremely", "highly", "significantly", "dramatically", "substantially", "remarkably", "undoubtedly", "absolutely"]), "adverb"),
    ("31", alt(["utilize", "utilizes", "utilizing", "utilization", "facilitate", "facilitates", "commence", "initiate", "endeavor", "ascertain", "numerous", "prior to", "subsequently", "in the event that"]), "inflated word"),
    ("32", r"\b(?:the (?:result|answer|catch|secret|best part|kicker|truth))\?|\band that changes everything\b", "mannered prose"),
    ("29", r"\b(?:is|are|was|were|been|being)\s+(?:\w+ly\s+)?\w+(?:ed|en)\s+by\b", "passive with 'by' (see T4)"),
    # Transfer from Vietnamese
    ("T1", r"\bnowadays\b|\bin the (?:era|age) of\b|\bin the digital (?:age|era)\b|\bas we all know\b|\bin the context of (?:globalization|integration)\b|\bit cannot be denied\b|\btechnology 4\.0\b|\bindustry 4\.0\b", "calqued opener"),
    ("T2", r"\bvery (?:important|good|necessary|useful|easy|nice|big|small|much|many|interesting|helpful)\b|\bso many\b|\bextremely necessary\b|\bsuper (?:fast|easy|cheap|good)\b|\bcompletely free\b", "empty intensifier"),
    ("T3", r"\bthe (?:use|usage|development|implementation|application|improvement|creation|management) of\b|\bcarry out\b|\bmake a decision on\b|\bperform the\b", "calqued nominalization"),
    ("T5", r"\b(?:is|was|are|be)\s+(?:very\s+)?(?:good|great|bad|big|new|simple|useful|perfect)\s+(?:idea|way|choice|option|example|solution|tool|place|question|start)\b|\bin the (?:19|20)\d\d\b|\bthe social media\b|\b(?:is|am|was) (?:designer|developer|teacher|student|engineer|marketer|freelancer)\b", "article check"),
    ("T6", r"\b(?:informations|advices|feedbacks|equipments|softwares|knowledges|homeworks|furnitures|evidences|staffs|traffics|researches)\b|\b(?:an?|many) (?:advice|information|feedback|equipment|software|knowledge|homework|furniture|evidence|research)\b", "countability"),
    ("T8", r"\b(?:discuss(?:ed|es|ing)? about|mention(?:ed|s|ing)? about|explain me|help(?:s|ed)? (?:you|them|us|people) to\b|make (?:you|them|us) can|return(?:ed|s)? back|reply back|until now|despite of|according to me|(?:price|prices|cost) (?:is|are) (?:cheap|expensive)|cheap price|it has (?:many|a lot of) (?:people|ways)|learn knowledge|open the light|raise up|take care about|interested about|depend in|in the other hand|make a research|can able to)\b", "calque"),
    ("T10", r"(?:^|[.!?]\s+)(?:This|The|Our|My) \w+(?: \w+)?, (?:it|they) (?:is|are|was|were)\b|\bfor me, I think\b|\bAbout \w+(?: \w+)?, (?:we|I|it)\b", "topic-comment"),
    ("T11", r"\bdear readers\b|\bwe would like to inform\b|\bhereby\b|\baforementioned\b|\bplease kindly\b|\bwe are (?:honored|honoured|proud) to (?:introduce|present)\b|\bthank you for reading\b", "too formal"),
    ("T12", r"\b\d{1,3}(?:\.\d{3})+(?![\d.])|\b\d+,\d+\s?%|\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d+(?:km|kg|cm|mm|ml)\b|\d\s+%|\b\d{1,2}h\s?-\s?\d{1,2}h\b", "Vietnamese-style format"),
    ("B1", r"\b(?:in this (?:article|post|blog post|blog|guide)|this (?:article|post) will)\b", "throat-clearing"),
]
COMPILED = [(r, re.compile(p, F), n) for r, p, n in PATTERNS]
SUBORDINATORS = ("if", "when", "although", "though", "because", "after", "before", "once", "while", "since", "as", "unless", "whether", "even", "until", "whenever", "where")
SUBJECT_STARTS = {"i", "we", "you", "it", "they", "he", "she", "this", "that", "these", "those", "the", "our", "my", "your", "their", "his", "her"}
SMALL = {"a", "an", "the", "of", "to", "in", "for", "and", "or", "on", "with", "vs", "at", "by", "but", "is", "your", "you"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728]")
LABEL_HEADINGS = re.compile(r"^#{2,6}\s*(?:introduction|conclusion|overview|summary|final thoughts|wrapping up|key takeaways|the bottom line)\s*$", F)


def strip_protected(text):
    out, fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append("")
            continue
        if fence or line.lstrip().startswith(">"):
            out.append("")
            continue
        out.append(re.sub(r"`[^`]*`", " ", line))
    return out


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def scan(text, max_per_rule=8, keyword=None):
    text = unicodedata.normalize("NFC", text)
    lines = strip_protected(text)
    hits = []

    def add(rule, ln, excerpt, note):
        hits.append({"rule": rule, "line": ln, "excerpt": excerpt.strip()[:100], "note": note})

    body_sentences = []
    first_para_done = False
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            continue
        is_heading = s.startswith("#")
        spans = defaultdict(list)
        for rule, rx, note in COMPILED:
            for m in rx.finditer(line):
                if any(m.start() < e and st < m.end() for st, e in spans[rule]):
                    continue
                spans[rule].append((m.start(), m.end()))
                a = max(0, m.start() - 20)
                add(rule, i, line[a:m.end() + 20], note)
        if is_heading:
            level = len(s) - len(s.lstrip("#"))
            words = re.findall(r"[A-Za-z][\w'-]*", s.lstrip("#"))
            content = [w for w in words[1:] if w.lower() not in SMALL]
            if level >= 2 and len(content) >= 2 and sum(w[0].isupper() for w in content) / len(content) >= 0.6:
                add("17", i, s, "title case heading")
            if EMOJI.search(s):
                add("18", i, s, "emoji in heading")
            if LABEL_HEADINGS.match(s):
                add("B2", i, s, "label heading")
            continue
        if re.match(r"^[-*+]\s", s) and EMOJI.search(s):
            add("18", i, s, "emoji in bullet")
        if re.match(r"^(?:[-*+]|\d+\.)?\s*(?:\S\s+)?\*\*[^*]{1,40}(?::\*\*|\*\*\s*:)", s):
            add("16", i, s, "inline-header list")
        if not s.startswith(("-", "*", "+", "|")) and not re.match(r"^\d+\.", s):
            for m in re.finditer(r"[a-z]:\s+[a-z]", s):
                rest = re.split(r"[.!?]", s[m.end():], maxsplit=1)[0]
                if "," in rest or " and " in rest or " or " in rest:
                    continue  # colon before a list is fine
                add("14", i, s[max(0, m.start() - 30):m.end() + 30], "colon as connector")
        sents = sentences(s)
        if not s.startswith("|"):
            body_sentences.extend(sents)
            if len(sents) > 5:
                add("B4", i, s[:80] + "…", f"paragraph of {len(sents)} sentences")
        for sent in sents:
            n = len(re.findall(r"[\w'-]+", sent))
            if n > 35:
                add("28", i, sent[:90] + "…", f"{n}-word sentence")
            first = sent.split(" ", 1)[0].lower().strip(",")
            if first in SUBJECT_STARTS and re.search(r",\s+(?:it|this|they|we|he|she|you)\s+(?:is|are|was|were|has|have|will|can|'s|'re)\b", sent, F):
                add("T9", i, sent[:90], "possible comma splice")
        # 32: stacked one-word fragments
        if re.search(r"(?:\b\w+\.\s+){2,}\b\w+\.", s) and all(len(x.split()) == 1 for x in re.findall(r"\b\w+\.", s)[:3]):
            if re.search(r"(?:^|\.\s)(\w+)\.\s(\w+)\.\s(\w+)\.", s):
                add("32", i, s[:80], "stacked fragments")
        if not first_para_done and not s.startswith(("-", "*", "|")):
            first_para_done = True
            if re.match(r"(?:nowadays|in today's|in the (?:era|age|digital)|as we all know|have you ever|imagine|in this (?:article|post))", s, F):
                add("B1", i, s[:80], "opening doesn't lead with the point")

    joined = "\n".join(lines)
    words = len(re.findall(r"[\w'-]+", joined))
    bold = len(re.findall(r"\*\*[^*]+\*\*", joined))
    if words and bold / words * 100 > 2:
        add("15", 0, f"{bold} bold phrases / {words} words", "bold overuse")
    if re.search(r"[“”]", joined) and re.search(r'"', joined):
        add("19", 0, "both curly and straight quotes", "mixed quotes")
    lens = [len(x.split()) for x in body_sentences if len(x.split()) > 2]
    if len(lens) >= 8:
        mean = statistics.mean(lens)
        cv = statistics.pstdev(lens) / mean if mean else 0
        if cv < 0.35:
            add("B4", 0, f"mean {mean:.0f} words, variation {cv:.2f}", "uniform sentence length")
    syn = [w for w in ("customer", "client", "user", "buyer", "shopper") if re.search(rf"\b{w}s?\b", joined, F)]
    if len(syn) >= 3:
        add("11", 0, ", ".join(syn), "possible synonym cycling")
    seo = None
    if keyword:
        kw = keyword.lower()
        low = joined.lower()
        title = next((l for l in lines if l.startswith("# ")), "")
        first100 = " ".join(re.findall(r"[\w'-]+", "\n".join(l for l in lines if l and not l.startswith("#"))))
        first100 = " ".join(first100.split()[:100]).lower()
        h2 = [l for l in lines if l.startswith("## ")]
        count = low.count(kw)
        toks = re.findall(r"\w+", kw)

        def has(textpart):
            t = textpart.lower()
            if kw in t:
                return True
            ws = re.findall(r"\w+", t)
            span = len(toks) + 3
            for st in range(max(1, len(ws) - span + 1)):
                win = ws[st:st + span]
                if all(any(w.startswith(k) for w in win) for k in toks):
                    return True
            return False
        seo = {
            "keyword": keyword,
            "count": count,
            "per_100_words": round(count / words * 100, 2) if words else 0,
            "in_title": has(title),
            "in_first_100_words": has(first100),
            "in_an_h2": any(has(h) for h in h2),
        }
        missing = [k for k in ("in_title", "in_first_100_words", "in_an_h2") if not seo[k]]
        if missing:
            add("B8", 0, ", ".join(missing), "keyword placement missing")
        if seo["per_100_words"] > 1.5:
            add("B8", 0, f"{count} uses in {words} words", "keyword stuffing")

    by_rule = defaultdict(list)
    for h in hits:
        by_rule[h["rule"]].append(h)
    total = len(hits)
    density = round(total / words * 1000, 1) if words else 0.0
    level = "clean" if density < 5 else "light" if density < 15 else "heavy"
    res = {
        "words": words,
        "total_hits": total,
        "per_1000_words": density,
        "level": level,
        "by_rule": {r: {"count": len(v), "hits": v[:max_per_rule]} for r, v in sorted(by_rule.items(), key=lambda kv: -len(kv[1]))},
    }
    if seo:
        res["seo"] = seo
    return res


def read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def report(res, name=""):
    print(f"== {name + ' ' if name else ''}{res['words']} words | {res['total_hits']} flags | {res['per_1000_words']}/1,000 words | level: {res['level']}")
    if "seo" in res:
        s = res["seo"]
        print(f"   keyword '{s['keyword']}': {s['count']}x, title={s['in_title']}, first100={s['in_first_100_words']}, h2={s['in_an_h2']}")
    for rule, d in res["by_rule"].items():
        print(f"\n[{rule}] x{d['count']}")
        for h in d["hits"]:
            loc = f"line {h['line']}" if h["line"] else "whole text"
            print(f"  {loc}: {h['excerpt']}  ({h['note']})")
        if d["count"] > len(d["hits"]):
            print(f"  … {d['count'] - len(d['hits'])} more")


def main():
    ap = argparse.ArgumentParser(description="Scan English for AI tells and Vietnamese-transfer errors (unslop rule ids).")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument("--keyword")
    ap.add_argument("--max-per-rule", type=int, default=8)
    a = ap.parse_args()
    try:
        if a.compare:
            b, f = (scan(read(p), a.max_per_rule, a.keyword) for p in a.compare)
            if a.json:
                print(json.dumps({"before": b, "after": f}, ensure_ascii=False, indent=2))
                return
            print(f"Before: {b['total_hits']} flags, {b['per_1000_words']}/1,000 ({b['level']}), {b['words']} words")
            print(f"After:  {f['total_hits']} flags, {f['per_1000_words']}/1,000 ({f['level']}), {f['words']} words")
            if b["words"]:
                print(f"Length change: {round((f['words'] - b['words']) / b['words'] * 100)}%")
            if f["by_rule"]:
                report(f, "After, details:")
            return
        if not a.files:
            ap.error("give a file or '-'")
        res = {p: scan(read(p), a.max_per_rule, a.keyword) for p in a.files}
        if a.json:
            print(json.dumps(res if len(res) > 1 else next(iter(res.values())), ensure_ascii=False, indent=2))
        else:
            for p, r in res.items():
                report(r, p if len(res) > 1 else "")
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
