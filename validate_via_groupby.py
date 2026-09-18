"""Validate the dashboard's headline figures against the API using group_by —
one call per question, exact counts, no sampling. This is the technique the
"Analyzing your Institution" guide recommends and that I did not use.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

INST = "I186143895"
F = f"authorships.institutions.lineage:{INST},publication_year:2016-2026"
BASE = "https://api.openalex.org/works"
calls = 0


def get(params):
    global calls
    calls += 1
    url = BASE + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "validate/1.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"__err": e.code, "__body": e.read().decode("utf-8", "replace")[:200]}


payload = json.load(open("payload.json", encoding="utf-8"))
META = payload["meta"]
I = {c: i for i, c in enumerate(payload["cols"])}
R = payload["rows"]
T = payload["tables"]
print("dashboard snapshot :", META["fetched"], "|", META["n"], "works\n")

# ---- 1. total count: has the corpus drifted since the snapshot? ----
d = get({"filter": F, "per_page": 1})
live_total = d["meta"]["count"]
print(f"total works        live={live_total:<7} snapshot={META['n']:<7} "
      f"drift={live_total - META['n']:+d}")

# ---- 2. open-access mix ----
d = get({"filter": F, "group_by": "open_access.oa_status"})
live_oa = {g["key"]: g["count"] for g in d.get("group_by", [])}
mine_oa = {}
for r in R:
    k = T["oa"][r[I["oa"]]]
    mine_oa[k] = mine_oa.get(k, 0) + 1
print("\nopen access        live / snapshot")
for k in sorted(set(list(live_oa) + list(mine_oa)), key=lambda x: -live_oa.get(x, 0)):
    print(f"  {k:<10} {live_oa.get(k, 0):>7} / {mine_oa.get(k, 0):>7}")

# ---- 3. SDG coverage ----
d = get({"filter": F, "group_by": "sustainable_development_goals.id"})
live_sdg_total = sum(g["count"] for g in d.get("group_by", []))
mine_sdg_total = sum(len(r[I["sdg"]]) for r in R)
print(f"\nSDG tag instances  live={live_sdg_total:<7} snapshot={mine_sdg_total}")

# ---- 4. works with NO source (the derived-source population) ----
for flt in ("primary_location.source.id:null", "has_doi:true"):
    d = get({"filter": F + "," + flt, "per_page": 1})
    if "__err" in d:
        print(f"\nfilter {flt:<38} NOT SUPPORTED")
    else:
        print(f"\nfilter {flt:<38} live={d['meta']['count']}")
print(f"  snapshot works with no OpenAlex source : {META['src_absent_in_openalex']}")
print(f"  of those, rebuilt from the DOI         : {META['src_derived']}")

# ---- 5. type mix (sanity on the conference-paper story) ----
d = get({"filter": F, "group_by": "type"})
live_ty = {g["key"].rsplit("/", 1)[-1]: g["count"] for g in d.get("group_by", [])}
mine_ty = {}
for r in R:
    k = T["ty"][r[I["ty"]]]
    mine_ty[k] = mine_ty.get(k, 0) + 1
print("\nwork type          live / snapshot  (top 6)")
for k in sorted(live_ty, key=lambda x: -live_ty[x])[:6]:
    print(f"  {k:<20} {live_ty[k]:>6} / {mine_ty.get(k, 0):>6}")

# ---- 6. does lineage pull in the health network? ----
print("\n-- institutions in Lehigh's lineage --")
d = get({"filter": F, "group_by": "authorships.institutions.lineage", "per_page": 200})
for g in d.get("group_by", [])[:8]:
    print(f"  {g['count']:>6}  {g.get('key_display_name')}")

print(f"\nAPI calls used: {calls}")
print(f"cost at $0.10/1,000 list calls: ${calls * 0.0001:.4f}")
print("keyless budget $0.10/day  |  free-key budget $1.00/day")
