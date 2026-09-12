"""Extract the library's OA waiver records and match them to the OpenAlex
corpus by DOI, producing waivers.json for the dashboard build.

Deliberately EXCLUDES the author email addresses and names in the source
sheet: the dashboard is a public web page, and none of that is needed to
flag a work as library-supported.
"""
import json
import re
import datetime
import openpyxl

SRC = r"C:\Users\pjh315\Downloads\Open Access (OA) Publishing Waivers Tracking 09112026.xlsx"
SHEET = "Data - do not edit"


def norm_doi(v):
    if not v:
        return None
    s = str(v).strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    s = re.sub(r"^doi:\s*", "", s)
    s = s.strip().rstrip(".")
    return s or None


def year_of(v):
    if isinstance(v, datetime.datetime):
        return v.year
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        m = re.search(r"(20\d\d)", v)
        if m:
            return int(m.group(1))
    return None


wb = openpyxl.load_workbook(SRC, data_only=True, read_only=True)
ws = wb[SHEET]
rows = list(ws.iter_rows(values_only=True))
head = [("" if c is None else str(c).strip()) for c in rows[0]]
idx = {h: i for i, h in enumerate(head) if h}


def cell(r, name):
    i = idx.get(name)
    if i is None or i >= len(r):
        return None
    v = r[i]
    return v if v is not None and str(v).strip() != "" else None


recs, no_doi, years = [], 0, {}
for r in rows[1:]:
    if not any(c is not None and str(c).strip() != "" for c in r):
        continue
    doi = norm_doi(cell(r, "DOI or DOI Link"))
    ay = year_of(cell(r, "Agreement Year")) or year_of(cell(r, "Approval or Accepted Date"))
    if ay:
        years[ay] = years.get(ay, 0) + 1
    if not doi:
        no_doi += 1
        continue
    apc = cell(r, "APC List Price")
    try:
        apc = round(float(apc)) if apc is not None else None
    except (TypeError, ValueError):
        apc = None
    recs.append({
        "doi": doi,
        "ay": ay,
        "oat": (str(cell(r, "OA Type (Gold or Hybrid)") or "").strip() or None),
        "pub": (str(cell(r, "Publisher") or "").strip() or None),
        "apc": apc,
        "lic": (str(cell(r, "License Type") or "").strip() or None),
        "dept": (str(cell(r, "Department") or "").strip() or None),
        "coll": (str(cell(r, "College") or "").strip() or None),
    })

print(f"data rows with content : {sum(years.values())}")
print(f"rows carrying a DOI    : {len(recs)}")
print(f"rows with no DOI       : {no_doi}")
print("by agreement year      :", dict(sorted(years.items())))

# dedupe on DOI (a DOI can appear twice if tracked at two stages)
by_doi = {}
for rec in recs:
    by_doi.setdefault(rec["doi"], rec)
print(f"distinct DOIs          : {len(by_doi)}")

# ---- match against the OpenAlex corpus ----
works = json.load(open("works.json", encoding="utf-8"))
corpus = {}
for w in works:
    d = norm_doi(w.get("doi"))
    if d:
        corpus[d] = w
print(f"\ncorpus works with a DOI: {len(corpus)} of {len(works)}")

matched, unmatched = {}, []
for d, rec in by_doi.items():
    if d in corpus:
        matched[d] = rec
    else:
        unmatched.append(rec)
print(f"matched to corpus      : {len(matched)}  ({len(matched)/len(by_doi)*100:.1f}%)")
print(f"unmatched              : {len(unmatched)}")
uy = {}
for rec in unmatched:
    uy[rec["ay"]] = uy.get(rec["ay"], 0) + 1
print("unmatched by year      :", dict(sorted((k, v) for k, v in uy.items() if k)))
print("\nfirst 8 unmatched DOIs:")
for rec in unmatched[:8]:
    print("  ", rec["ay"], rec["pub"], rec["doi"])

# what the matched set looks like against OpenAlex's own OA status
from collections import Counter
oastat = Counter(corpus[d]["oa"] for d in matched)
print("\nOpenAlex oa_status of matched works:", dict(oastat))
print("sheet OA type of matched works     :", dict(Counter(r["oat"] for r in matched.values())))
print("publishers                         :", dict(Counter(r["pub"] for r in matched.values()).most_common(10)))
apcs = [r["apc"] for r in matched.values() if r["apc"]]
print(f"APC list price: n={len(apcs)} total=${sum(apcs):,} median=${sorted(apcs)[len(apcs)//2]:,}")
print("colleges:", dict(Counter(r["coll"] for r in matched.values())))

out = {
    "source": "Open Access (OA) Publishing Waivers Tracking 09112026.xlsx",
    "years_covered": sorted(y for y in years if y),
    "n_sheet_rows": sum(years.values()),
    "n_with_doi": len(by_doi),
    "n_matched": len(matched),
    "records": matched,
}
with open("waivers.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
print("\nwrote waivers.json")
