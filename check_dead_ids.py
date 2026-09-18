"""Find OpenAlex work IDs that no longer resolve, and write dead_ids.json.

Works without a DOI are linked by their OpenAlex ID, so when OpenAlex merges a
duplicate or splits a "mega-work" the row's only link dies. Since September 2026
that happens routinely: ~2.7M figshare items stopped being standalone works, and
mega-works are being split, so IDs redirect or disappear.

Only no-DOI works need checking (a DOI link never depends on an OpenAlex ID), so
this is ~400 ids in 9 batched calls. Run it after fetch_openalex.py and before
pack.py; pack.py marks the affected rows so the page shows the title without a
dead link. If dead_ids.json is absent, pack.py simply skips the marking.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

BATCH = 50
calls = 0


def get(params):
    global calls
    calls += 1
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "dead-id-check/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                import time
                time.sleep(2 ** attempt)
                continue
            raise
    return {}


works = json.load(open("works.json", encoding="utf-8"))
no_doi = [w for w in works if not w.get("doi") and w.get("id")]
ids = [w["id"] for w in no_doi]
print(f"works in corpus            : {len(works)}")
print(f"without a DOI (ID-linked)  : {len(ids)}")

alive = set()
for i in range(0, len(ids), BATCH):
    chunk = ids[i:i + BATCH]
    d = get({"filter": "openalex:" + "|".join(chunk), "select": "id", "per_page": BATCH})
    for w in d.get("results", []):
        alive.add(w["id"].rsplit("/", 1)[-1])
    print(f"  checked {min(i + BATCH, len(ids))}/{len(ids)}")

dead = sorted(set(ids) - alive)
print(f"\nIDs that no longer resolve : {len(dead)} "
      f"({len(dead) / max(len(ids), 1) * 100:.1f}% of ID-linked rows)")
for w in no_doi:
    if w["id"] in dead[:6]:
        print(f"   {w['id']}  {w['ty'].rsplit('/', 1)[-1]:<22} {w['t'][:52]}")

with open("dead_ids.json", "w", encoding="utf-8") as fh:
    json.dump({"checked": len(ids), "dead": dead}, fh, separators=(",", ":"))
print(f"\nwrote dead_ids.json  |  {calls} API calls (~${calls * 0.0001:.4f})")
