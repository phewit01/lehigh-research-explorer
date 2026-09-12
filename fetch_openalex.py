"""Fetch Lehigh University (OpenAlex I186143895) works 2016-2026 and trim to a
compact JSON payload for the dashboard."""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

# Sub-institutional units are not modelled by OpenAlex. The only source is the
# publisher-supplied raw affiliation string, so we lift the unit clause out of it
# and normalise downstream in pack.py. ~77% of Lehigh authorships carry one.
UNIT_RE = re.compile(
    r"(?:^|,\s*)\(?\s*((?:Department|Departments|Dept\.?|School|College|Institute|"
    r"Centre|Center|Division|Program|Programme|Laboratory|Lab)\b[^,;()]{0,80})", re.I)

INST = "I186143895"
YEARS = "2016-2026"
SELECT = ",".join([
    "id", "doi", "title", "publication_year", "publication_date", "type",
    "cited_by_count", "fwci", "open_access", "authorships", "primary_location",
    "primary_topic", "is_retracted", "referenced_works_count",
    # 'grants' was retired; funder data now lives in these two fields.
    "funders", "awards",
    "sustainable_development_goals",
])
BASE = "https://api.openalex.org/works"
UA = "LehighDashboard/1.0 (research dashboard; contact via OpenAlex polite pool)"


def get(url):
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # transient 429/5xx/network
            wait = 2 ** attempt
            print(f"  retry {attempt+1} in {wait}s ({e})", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit("giving up on " + url)


def short_id(oa_id):
    return oa_id.rsplit("/", 1)[-1] if oa_id else None


def trim(w):
    auths = w.get("authorships") or []
    names, lehigh, insts, countries = [], [], set(), set()
    units, bare = [], []
    # Tri-state: a Lehigh author is corresponding / someone else is / nobody is
    # marked at all. Conflating the last two would overstate the middle case.
    any_corr, lehigh_corr, corr_names = False, False, []
    for a in auths:
        nm = (a.get("author") or {}).get("display_name")
        if nm and len(names) < 25:
            names.append(nm)
        is_lehigh = False
        for i in a.get("institutions") or []:
            iid = short_id(i.get("id"))
            if iid == INST or INST in [short_id(x) for x in (i.get("lineage") or [])]:
                is_lehigh = True
            elif i.get("display_name"):
                insts.add(i["display_name"])
            if i.get("country_code"):
                countries.add(i["country_code"])
        for c in a.get("countries") or []:
            countries.add(c)
        if a.get("is_corresponding"):
            any_corr = True
            if is_lehigh:
                lehigh_corr = True
                if nm and nm not in corr_names:
                    corr_names.append(nm)
        if is_lehigh and nm and nm not in lehigh:
            lehigh.append(nm)
        if is_lehigh:
            # Only strings the API itself tied to Lehigh, so a co-author's
            # department at another university can never leak in.
            for aff in a.get("affiliations") or []:
                if INST not in [short_id(x) for x in (aff.get("institution_ids") or [])]:
                    continue
                raw = aff.get("raw_affiliation_string") or ""
                m = UNIT_RE.search(raw)
                if m:
                    u = m.group(1).strip()
                    if u not in units:
                        units.append(u)
                elif raw and raw not in bare:
                    # publishers often append the corresponding author's email
                    bare.append(re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "[email removed]", raw))

    oa = w.get("open_access") or {}
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    pt = w.get("primary_topic") or {}

    # Publisher: keep the imprint as recorded AND the top of OpenAlex's own
    # host-organization lineage, so imprints can be rolled up to the parent
    # company without hand-written string merging. Lineage runs child -> parent.
    lineage = src.get("host_organization_lineage_names") or []
    parent = lineage[-1] if lineage else (src.get("host_organization_name") or "")

    # SDG ids carry the goal number (https://metadata.un.org/sdg/7), which is
    # far more robust than matching the display name's inconsistent casing.
    sdgs = []
    for g in w.get("sustainable_development_goals") or []:
        gid = (g.get("id") or "").rstrip("/").rsplit("/", 1)[-1]
        if gid.isdigit() and g.get("score") is not None:
            sdgs.append([int(gid), round(float(g["score"]), 3)])
    sdgs.sort(key=lambda x: -x[1])
    funders = []
    for f in w.get("funders") or []:
        nm = f.get("display_name")
        if nm and nm not in funders:
            funders.append(nm)
    awards = []
    for g in w.get("awards") or []:
        aid = g.get("funder_award_id")
        nm = g.get("funder_display_name")
        if nm and nm not in funders:
            funders.append(nm)
        if aid and aid not in awards:
            awards.append(str(aid)[:40])

    title = w.get("title") or "(untitled)"
    return {
        "id": short_id(w.get("id")),
        "t": title[:400],
        "y": w.get("publication_year"),
        "d": w.get("publication_date"),
        "ty": (w.get("type") or "other"),
        "c": w.get("cited_by_count") or 0,
        "f": round(w["fwci"], 2) if w.get("fwci") is not None else None,
        "oa": oa.get("oa_status") or "unknown",
        "src": (src.get("display_name") or "")[:160],
        "pub": (src.get("host_organization_name") or "")[:120],
        "pubp": parent[:120],                       # top-level parent company
        "stype": src.get("type") or "",             # journal / repository / conference / ...
        "doaj": 1 if src.get("is_in_doaj") else 0,
        "sdg": sdgs[:6],
        "top": pt.get("display_name"),
        "sub": ((pt.get("subfield") or {}).get("display_name")),
        "fld": ((pt.get("field") or {}).get("display_name")),
        "dom": ((pt.get("domain") or {}).get("display_name")),
        "la": lehigh[:30],
        "na": len(auths),
        "au": names,
        "ci": sorted(insts)[:40],
        "cc": sorted(countries),
        "co": 1 if lehigh_corr else (0 if any_corr else -1),
        "cn": corr_names[:6],
        "un": units[:6],          # raw Lehigh unit strings, normalised in pack.py
        "bare": bare[:1],         # affiliation with no unit clause, for auditing
        "fu": funders[:14],
        "aw": awards[:10],
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "rt": bool(w.get("is_retracted")),
        "rf": w.get("referenced_works_count") or 0,
    }


def main():
    out, cursor, page = [], "*", 0
    while cursor:
        params = {
            "filter": f"authorships.institutions.lineage:{INST},publication_year:{YEARS}",
            "select": SELECT,
            "per_page": "200",
            "cursor": cursor,
        }
        data = get(BASE + "?" + urllib.parse.urlencode(params))
        page += 1
        for w in data["results"]:
            out.append(trim(w))
        cursor = data["meta"].get("next_cursor")
        print(f"page {page}: {len(out)}/{data['meta']['count']}")
        if not data["results"]:
            break
    with open("works.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    print("wrote works.json", len(out))


if __name__ == "__main__":
    main()
