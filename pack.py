"""Trim works.json into a compact dashboard payload with shared string tables.

Departments are DERIVED, not supplied by OpenAlex: the publisher's raw
affiliation string is the only source, so the clause is lifted in
fetch_openalex.py and normalised to a canonical unit here. A string naming
several units maps to all of them, so interdisciplinary works count once per
unit. Strings that name only a college are kept as such rather than guessed
down to a department, and works with no unit clause at all get their own
bucket instead of being silently dropped.
"""
import json
import re
from collections import Counter

works = json.load(open("works.json", encoding="utf-8"))

# Library APC-waiver records, matched to the corpus by DOI in waivers.py.
# Optional: the build still works without it, just without the toggle.
# Set INCLUDE_APC = False to keep list prices off the published page.
INCLUDE_APC = True
try:
    WAIVERS = json.load(open("waivers.json", encoding="utf-8"))
except FileNotFoundError:
    WAIVERS = None
    print("note: waivers.json absent — library-supported toggle will be omitted")

# OpenAlex IDs that no longer resolve, from check_dead_ids.py. A no-DOI row is
# linked by its OpenAlex ID, and since Sept 2026 those IDs are routinely merged
# or retired, so the link dies. Marked rather than linked.
try:
    DEAD = set(json.load(open("dead_ids.json", encoding="utf-8"))["dead"])
except (FileNotFoundError, KeyError):
    DEAD = set()
    print("note: dead_ids.json absent — run check_dead_ids.py to flag retired IDs")


def norm_doi(v):
    if not v:
        return None
    s = str(v).strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    return s.rstrip(".") or None


# Publishers routinely append the corresponding author's email to the raw
# affiliation string. Those strings are shown in the audit tooltip, so they
# must be redacted before anything reaches a public page — the tooltip only
# needs to prove that no unit was named, which the rest of the string does.
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def redact(s):
    if not s:
        return s
    return EMAIL_RE.sub("[email removed]", s)


def clean(s):
    """Collapse whitespace runs. OpenAlex source names carry stray double
    spaces ("2018  AIAA Aerospace Sciences Meeting"), and collation ranks a
    space below a digit — so an uncleaned name sorts somewhere the reader,
    seeing HTML-collapsed whitespace, cannot predict."""
    if not s:
        return s
    return re.sub(r"\s+", " ", s).strip()

# (canonical unit, alias patterns matched against the normalised string)
DEPTS = [
    ("Chemical & Biomolecular Engineering", [r"chemical and (bio|bi)molecular engineering",
                                             r"chemical engineering", r"chemical and amp"]),
    ("Civil & Environmental Engineering",   [r"civil and environmental engineering",
                                             r"civil engineering", r"civil and amp"]),
    ("Mechanical Engineering & Mechanics",  [r"mechanical engineering"]),
    ("Materials Science & Engineering",     [r"materials? science and engineering",
                                             r"materials? science and amp"]),
    ("Electrical & Computer Engineering",   [r"electrical", r"\bece\b"]),
    ("Computer Science & Engineering",      [r"computer science"]),
    ("Industrial & Systems Engineering",    [r"industrial and systems? engineering"]),
    ("Bioengineering",                      [r"bioengineering", r"biomedical engineering"]),
    ("Biological Sciences",                 [r"biological sciences?", r"biology"]),
    ("Chemistry",                           [r"\bchemistry\b"]),
    ("Physics",                             [r"\bphysics\b"]),
    ("Mathematics",                         [r"\bmathematics\b", r"\bmath\b"]),
    ("Earth & Environmental Sciences",      [r"earth and environmental scienc", r"earth and amp"]),
    ("Psychology",                          [r"psychology"]),
    ("Education & Human Services",          [r"education and human services", r"teaching learning",
                                             r"special education", r"school psychology"]),
    ("Community & Population Health",       [r"community and population health", r"population health",
                                             r"community and global health", r"community health"]),
    ("Biostatistics & Health Data Science", [r"biostatistics"]),
    ("Economics",                           [r"economics"]),
    ("Management",                          [r"\bmanagement\b"]),
    ("Marketing",                           [r"\bmarketing\b"]),
    ("Accounting",                          [r"accounting"]),
    ("Finance",                             [r"\bfinance\b"]),
    ("Decision & Technology Analytics",     [r"decision and technology analytics"]),
    ("Supply Chain & Business Analytics",   [r"supply chain"]),
    ("Sociology & Anthropology",            [r"sociology", r"anthropology"]),
    ("Political Science",                   [r"political science"]),
    ("International Relations",             [r"international relations"]),
    ("Philosophy",                          [r"philosophy"]),
    ("History",                             [r"\bhistory\b"]),
    ("English",                             [r"\benglish\b"]),
    ("Modern Languages & Literatures",      [r"modern languages"]),
    ("Journalism & Communication",          [r"journalism"]),
    ("Religion Studies",                    [r"religion"]),
    ("Art, Architecture & Design",          [r"\bart\b", r"architecture"]),
    ("Theatre",                             [r"theatre|theater"]),
    ("Music",                               [r"\bmusic\b"]),
    ("Centers & institutes",                [r"\bcenter\b|\bcentre\b|\binstitute\b|\blaborator|\blab\b"]),
]
DEPTS = [(name, [re.compile(p) for p in pats]) for name, pats in DEPTS]

# strings that name only a college — recorded as such, never guessed downward
COLLEGE_ONLY = re.compile(r"^college of |^p ?c rossin|^rossin college")

NOT_STATED = "Not stated in affiliation"
COLLEGE_LEVEL = "College-level only (no department given)"

# Publisher buckets. The imprint -> parent merge is done by OpenAlex's own
# host_organization_lineage, NOT here. This map only renames a parent to the
# name people recognise: lineage tops out at the university that owns a press,
# and a couple of societies are unreadably long in a chart axis.
PUB_DISPLAY = {
    "University of Oxford": "Oxford University Press",
    "University of Cambridge": "Cambridge University Press",
    "Informa": "Taylor & Francis",
    "Institute of Physics": "IOP Publishing",
    "Institute of Electrical and Electronics Engineers": "IEEE",
    "Multidisciplinary Digital Publishing Institute": "MDPI",
}
PUB_REPO = "Repositories & preprint servers"
PUB_NONE = "No publisher recorded"

# ---- fallback for works OpenAlex holds with no source record at all ----
# 14% of the corpus, 1,240 of them conference papers: IEEE and ACM proceedings
# routinely arrive with a DOI but no registered venue. The DOI itself names the
# registrant, and for conference-heavy registrants the suffix often names the
# conference (10.1109/cvpr.2018.00143 -> IEEE, CVPR). Derived, and flagged.
from doi_registrants import REGISTRANTS

TYPE_WORD = {
    "conference-paper": "conference proceedings",
    "conference-abstract": "conference proceedings",
    "book-chapter": "book chapter",
    "book": "book",
    "reference-entry": "reference work",
    "preprint": "preprint",
    "report": "report",
    "article": "journal article",
    "review": "review",
    "dataset": "dataset",
    "peer-review": "peer review",
    "dissertation": "dissertation",
    "editorial": "editorial",
}
ACRONYM_RE = re.compile(r"^([a-z][a-z0-9]{1,11})[._\-/]")


def derive_source(w):
    """(source label, publisher) from the DOI when OpenAlex has no source."""
    doi = (w.get("doi") or "").lower()
    if "/" not in doi:
        return None, None
    prefix, suffix = doi.split("/", 1)
    ent = REGISTRANTS.get(prefix)
    if not ent:
        return None, None
    publisher, conf_style = ent
    ty = (w.get("ty") or "").rsplit("/", 1)[-1]

    acronym = None
    if conf_style and ty in ("conference-paper", "conference-abstract"):
        m = ACRONYM_RE.match(suffix)
        if m:
            a = re.sub(r"\d+$", "", m.group(1))      # IEEE appends record ids
            if 2 <= len(a) <= 8 and a.isalpha():
                acronym = a.upper()

    word = TYPE_WORD.get(ty)
    label = publisher + (" " + word if word else "")
    if acronym:
        label += f" ({acronym})"
    return label, publisher


def publisher_of(w):
    """(bucket, imprint) — bucket is what the chart ranks, imprint the detail."""
    imprint = (w.get("pub") or "").strip() or (w.get("src") or "").strip()
    if w.get("stype") == "repository":
        # A repository's host organisation is its operator, not its name: SSRN
        # would read "RELX Group", arXiv "Cornell University". Use the venue
        # name and drop the parenthetical operator it usually carries.
        name = (w.get("src") or "").strip() or imprint
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        return PUB_REPO, (name or "Unnamed repository")
    parent = (w.get("pubp") or "").strip()
    if not parent:
        return PUB_NONE, imprint
    return PUB_DISPLAY.get(parent, parent), (imprint or parent)


def norm(u):
    s = u.lower().strip()
    s = s.replace("&", " and ")
    s = re.sub(r"\bdepts?\.?\b", "department", s)
    s = re.sub(r"\bdepartments\b", "department", s)
    s = re.split(r"\blehigh\b", s)[0]          # address noise leaks in after the name
    s = re.sub(r"\bthe\b", " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


unmapped = Counter()


def depts_for(raw_units):
    out = []
    for u in raw_units:
        n = norm(u)
        if not n:
            continue
        body = re.sub(r"^department of |^department |^school of |^division of |^program in ", "", n)
        if COLLEGE_ONLY.match(body) or COLLEGE_ONLY.match(n):
            if COLLEGE_LEVEL not in out:
                out.append(COLLEGE_LEVEL)
            continue
        hit = False
        for name, pats in DEPTS:
            for p in pats:
                if p.search(body):
                    if name not in out:
                        out.append(name)
                    hit = True
                    break
        if not hit:
            unmapped[n] += 1
    return out


tables = {}


def interner(key):
    idx, order = {}, []

    def put(v):
        if v is None or v == "":
            return -1
        if v not in idx:
            idx[v] = len(order)
            order.append(v)
        return idx[v]
    tables[key] = order
    return put


put_src = interner("src");   put_top = interner("top")
put_sub = interner("sub");   put_fld = interner("fld")
put_dom = interner("dom");   put_ty = interner("ty")
put_oa = interner("oa");     put_inst = interner("inst")
put_ctry = interner("ctry"); put_dept = interner("dept")
put_fund = interner("fund"); put_pub = interner("pub")
put_imp = interner("imp")

rows = []
dept_hits = 0
pub_named = 0
sdg_tagged = 0
lw_hits = 0
src_absent = sum(1 for w in works if not (w.get("src") or "").strip())
for w in works:
    # Fill a missing source/publisher from the DOI registrant, flagged derived.
    src_label = clean(w.get("src") or "")
    derived = 0
    if not src_label:
        dl, dpub = derive_source(w)
        if dl:
            src_label = dl
            derived = 1
            if not (w.get("pubp") or "").strip() and w.get("stype") != "repository":
                w["pubp"] = dpub
                w["pub"] = w["pub"] or dpub
    w["src"] = src_label

    lw = None
    if WAIVERS:
        rec = WAIVERS["records"].get(norm_doi(w.get("doi")) or "")
        if rec:
            lw_hits += 1
            lw = {"ay": rec["ay"], "oat": rec["oat"], "pub": rec["pub"],
                  "lic": rec["lic"], "dept": rec["dept"], "coll": rec["coll"]}
            if INCLUDE_APC and rec.get("apc"):
                lw["apc"] = rec["apc"]
    bucket, imprint = publisher_of(w)
    if bucket not in (PUB_NONE, PUB_REPO):
        pub_named += 1
    if w["sdg"]:
        sdg_tagged += 1
    ds = depts_for(w["un"])
    if not ds:
        ds = [NOT_STATED]
    elif ds != [COLLEGE_LEVEL]:
        dept_hits += 1
    rows.append([
        w["id"][1:] if w["id"] and w["id"][0] == "W" else w["id"],
        clean(w["t"])[:300],
        w["y"],
        w["d"][5:] if w.get("d") else None,
        put_ty(w["ty"].rsplit("/", 1)[-1]),
        w["c"],
        w["f"],
        put_oa(w["oa"]),
        put_src(w["src"]),
        put_top(w["top"]),
        put_sub(w["sub"]),
        put_fld(w["fld"]),
        put_dom(w["dom"]),
        w["la"][:12],
        w["na"],
        [put_inst(i) for i in w["ci"][:12]],
        [put_ctry(c) for c in w["cc"]],
        w["doi"],
        1 if w["rt"] else 0,
        w["rf"],
        w["co"],                                   # -1 none / 0 other / 1 Lehigh
        w["cn"][:4],                               # Lehigh corresponding names
        [put_dept(d) for d in ds],
        [put_fund(f) for f in w["fu"][:10]],
        w["aw"][:6],
        (redact(w["bare"][0])[:110] if w["bare"] else None),
        put_pub(clean(bucket)),
        put_imp(clean(imprint)),
        [s[0] for s in w["sdg"]],                  # UN goal numbers, score >= 0.4
        lw,                                        # library APC waiver record, or null
        derived,                                   # 1 = source/publisher from DOI prefix
        1 if (w["id"] in DEAD and not w.get("doi")) else 0,   # retired OpenAlex ID
    ])

I_SRCD = -2          # 'srcd' column, second from the end of each row
payload = {
    "meta": {
        "institution": "Lehigh University",
        "openalex_id": "I186143895",
        "ror": "https://ror.org/012afjb06",
        "years": [2016, 2026],
        "n": len(rows),
        "fetched": "2026-09-11",
        "not_stated": NOT_STATED,
        "college_level": COLLEGE_LEVEL,
        "dept_coverage": round(dept_hits / len(rows) * 100, 1),
        "pub_coverage": round(pub_named / len(rows) * 100, 1),
        "src_derived": sum(r[I_SRCD] for r in rows),
        "ids_retired": sum(r[-1] for r in rows),
        "src_missing": sum(1 for w in works if not (w.get("src") or "").strip()),
        "src_absent_in_openalex": src_absent,
        "sdg_coverage": round(sdg_tagged / len(rows) * 100, 1),
        "pub_repo": PUB_REPO,
        "pub_none": PUB_NONE,
        "growth_periods": [[2016, 2020], [2021, 2025]],
        "lw": ({
            "n": lw_hits,
            "years": WAIVERS["years_covered"],
            "sheet_rows": WAIVERS["n_sheet_rows"],
            "with_doi": WAIVERS["n_with_doi"],
            "unmatched": WAIVERS["n_with_doi"] - WAIVERS["n_matched"],
            "apc": INCLUDE_APC,
        } if WAIVERS else None),
        "corr_coverage": round(sum(1 for w in works if w["co"] != -1) / len(rows) * 100, 1),
        "fund_coverage": round(sum(1 for w in works if w["fu"]) / len(rows) * 100, 1),
    },
    "tables": tables,
    "cols": ["id", "t", "y", "d", "ty", "c", "f", "oa", "src", "top", "sub",
             "fld", "dom", "la", "na", "ci", "cc", "doi", "rt", "rf",
             "co", "cn", "dept", "fund", "aw", "bare", "pub", "imp", "sdg", "lw",
             "srcd", "gone"],
    "rows": rows,
}

blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

# Hard gate: nothing with an email address ships. This page is public, and
# affiliation strings are an easy way for one to slip back in.
leaks = EMAIL_RE.findall(blob)
if leaks:
    raise SystemExit(
        f"ABORT: {len(leaks)} email address(es) would ship in payload.json, "
        f"e.g. {leaks[:3]}. Redact them before building."
    )

with open("payload.json", "w", encoding="utf-8") as fh:
    fh.write(blob)

print("works:", len(rows))
print("dept coverage (a real unit named):", payload["meta"]["dept_coverage"], "%")
print("funder coverage:", payload["meta"]["fund_coverage"], "%")
print("corresponding recorded:", payload["meta"]["corr_coverage"], "%")
for k, v in tables.items():
    print(f"  table {k}: {len(v)}")
print("\nunit strings that matched no canonical department "
      f"({sum(unmapped.values())} occurrences, {len(unmapped)} distinct) — top 25:")
for u, c in unmapped.most_common(25):
    print(f"  {c:5d}  {u}")
