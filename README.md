# Lehigh University Research Explorer

A filterable dashboard of Lehigh University affiliated research output, 2016–2026,
built from [OpenAlex](https://openalex.org). `index.html` is self-contained: the data
snapshot, CSS and JavaScript are all embedded, and the page makes no network calls at
runtime (only Google Fonts, which degrade to system fonts offline).

Live page: enable GitHub Pages on this repo (Settings → Pages → Deploy from branch → `main` / root).

## Data

- Source: OpenAlex institution [`I186143895`](https://openalex.org/I186143895) (ROR `012afjb06`),
  all works with ≥1 author affiliated to Lehigh or a unit in its lineage.
- 13,971 works, published 2016–2026. Snapshot taken 2026-09-11.
- OpenAlex data is CC0. The public API needs no key.

## Sharing a filtered view

Filters are written to the **query string**, so any view is a link. `Copy link` in the nav strip
copies the current one.

```
…/lehigh-research-explorer/?field=Engineering&cited=10&corr=lehigh&sdg=7
```

Only non-default values appear, so an unfiltered view has a clean URL. The hash is left to the
section anchors (`#s-publishing`), so navigation and filters never collide. Params naming data — a
field, author, funder, publisher — are validated against the loaded snapshot on the way in: a link
that names something a later refresh no longer contains drops that filter and says so in the
filter bar rather than silently rendering an empty page. Numbers are clamped and enum values
rejected, so a malformed link still loads a working page.

## Coverage, and what not to trust

| Field | Coverage | Notes |
|---|---|---|
| Works, citations, venue, type, open-access route | ~100% | Straight from OpenAlex |
| FWCI | 81% of works | Undefined for very recent/unclassified works; excluded from means, never counted as zero |
| Funder | 45% of works | Works naming no funder are absent, so funder counts are a **floor**, not a total |
| Corresponding author | 63% of works | Tri-state: Lehigh / elsewhere / **not recorded**. "Not recorded" is unknown, not negative |
| Publisher | 70% of works | Imprints rolled to parent via OpenAlex lineage; see below |
| SDG goal tags | 50% of works | Machine predictions at ≥0.4 confidence, not declarations |
| Library-supported OA | 410 works, **2024–2026 only** | From the Libraries' waiver sheet, not OpenAlex; see below |
| Department | 49% of works | **Derived**, see below |

**Departments are derived, not supplied.** OpenAlex has no department or college field.
The unit is parsed out of the publisher's raw affiliation string and normalised to a
canonical list in `pack.py`. Inherent limits:

- Only 49% of works name a unit at all; the rest say just "Lehigh University" and land in
  *unit not stated*. Hover a unit chip in the table to see the source string.
- Renamed units split a time series (Chemical Engineering → Chemical & Biomolecular Engineering).
- The string is what an author typed on that paper, so joint and courtesy appointments are invisible.
- Interdisciplinary strings count under every unit they name.
- A few hospital departments arrive via health-network records matched to Lehigh.

**Read & publish OA — one funding route, 2024–2026 only.** Sourced from Lehigh Libraries'
*Open Access (OA) Publishing Waivers Tracking* workbook (sheet `Data - do not edit`), matched to
the corpus by DOI in `waivers.py`. Of 450 rows, 442 carry a DOI and 410 corpus works matched
(92%); the 34 misses are nearly all very recent Elsevier and Wiley DOIs not yet in the snapshot.

**This flag covers APC waivers and discounts under read-and-publish agreements with publishers
only. It is not a measure of library support for open access generally** — the institutional
repository, subvention and membership funds, consultation and infrastructure support are all
absent from this sheet and therefore from the flag.

**The flag starts at agreement year 2024. Absence of the flag is not evidence that a work was
unsupported** — no data exists before 2024. Never compare flagged counts across the full
2016–2026 range. Agreement year is when the APC was approved, not when the article appeared:
they differ for 15 works, and one flagged article has a 2024 agreement with a 2023 publication
date.

Because the waiver data only exists from 2024, the **Rising & falling subfields** panel suppresses
itself whenever this filter is on, and explains why: its comparison needs works in both the
2016–2020 and 2021–2025 windows, and every subfield would otherwise read as rising from zero. The
same guard fires for any filter that empties one window (e.g. a 2024+ year range).

Two notes. First, **8 flagged works are `closed` in OpenAlex** despite being library-funded OA —
OpenAlex has not picked up the open version. Filter to *Library-supported* plus the *Closed*
access route to list them; they are worth reporting upstream. Second, **author names and email
addresses from the sheet are deliberately not carried into the page.** `pack.py` also redacts
emails out of raw affiliation strings (publishers embed corresponding-author addresses in them)
and **aborts the build** if any email would ship. Set `INCLUDE_APC = False` in `pack.py` to keep
APC list prices off the page as well.

To refresh this part, update the workbook path at the top of `waivers.py`, run it, then re-run
`pack.py` and `build.py`. The dashboard builds fine without `waivers.json` — the toggle is simply
omitted.

**Publishers.** The imprint→parent merge uses OpenAlex's own `host_organization_lineage`, not a
mapping written here — Nature Portfolio, Springer Science+Business Media and BioMed Central all
sit under Springer Nature (1,367), and the **Imprint** toggle splits them apart again. The
`PUB_DISPLAY` map in `pack.py` renames six parents for legibility only: lineage tops out at the
university that owns a press (OUP appeared as "University of Oxford"), and IEEE and MDPI were
appearing at full length. Repositories and preprint servers are bucketed separately using
`source.type == "repository"` and labelled by venue rather than host operator — otherwise SSRN
reads as "RELX Group" and arXiv as "Cornell University". They are ranked below a divider along
with "no publisher recorded", so neither tops the chart nor sets the bar scale.

**Rising & falling subfields** compares two equal five-year windows, 2016–2020 against 2021–2025.
2026 is excluded deliberately: it is a partial year and would drag every subfield downwards.
Subfields under 25 works across both windows are omitted, because small denominators generate
meaningless percentages.

**SDG wheel.** Spoke length encodes works, but a wedge's *area* grows faster than its value, so
the ranked list beside the wheel carries the exact figures. Goal colours are the official UN
palette — an external documented standard — and identity is always carried by the goal number and
name as well, never by hue alone.

**Colleges are deliberately not included.** Mapping departments to Lehigh's colleges would be
inference layered on a 49% sample, and the ambiguous cases (Bioengineering, Psychology,
Economics, Community & Population Health) are the ones most likely to mislead. Use Lehigh's
own faculty-activity system for anything evaluative.

## Refreshing the data

Requires Python 3 (standard library only — no pip install).

```bash
python fetch_openalex.py   # ~70 paged API calls -> works.json   (a few minutes)
python check_dead_ids.py   # 9 calls -> dead_ids.json  (retired OpenAlex IDs)
python pack.py             # normalise + intern -> payload.json
python build.py            # splice into template.html -> index.html
python validate_via_groupby.py   # optional: 7 calls, cross-check vs live data
```

Then commit and push `index.html`. Edit the year range at the top of `fetch_openalex.py`
to widen the corpus; edit the `DEPTS` crosswalk in `pack.py` to correct unit mapping.
`pack.py` prints any unit string that matched no canonical department, which is the list
to work from when extending the crosswalk.

`template.html` holds the page itself (markup, CSS, JS) with a `/*__DATA__*/` placeholder;
`build.py` emits both the standalone `index.html` and an Artifact-flavoured copy.

### Two rules, learned the hard way

Building this took **four full crawls of all 13,971 works where one would have done**, and
produced one figure that had to be publicly corrected. Both were avoidable. Read these before
touching `fetch_openalex.py`.

**1. Settle the whole field list before the first crawl, and validate it with one request.**

Each re-crawl here happened because a field was discovered late: `grants` turned out to be
retired (it is now `funders` + `awards`), then corresponding-author flags were wanted, then
publisher lineage and SDG tags. A crawl is ~70 requests and ~31 MB; validating the `select`
list costs *one* request:

```bash
# one request; fails loudly and names every valid field in the error body
curl "https://api.openalex.org/works?filter=authorships.institutions.lineage:I186143895&per_page=1&select=id,funders,awards,sustainable_development_goals"
```

Note that not every field OpenAlex returns is `select`-able, and the error body is the fastest
way to find out which. `primary_location.source` carries `host_organization_lineage_names`,
which is what the publisher rollup depends on — it is not in the quick reference below, only in
the returned object.

**2. For a rate, use `group_by` — it returns exact counts in one call.**

Cursor pagination does **not** return a random subset. Estimating department coverage from the
first 2,000 cursor results gave **77%**; the true corpus-wide figure is **49.4%**. The same
mistake produced a slice in which 97% of works appeared to be in the top 10% most-cited, which
is impossible.

Sampling is not the best fix — `group_by` is. One call gives exact counts for the whole corpus:

```bash
# exact open-access mix, whole corpus, one call
curl "https://api.openalex.org/works?filter=authorships.institutions.lineage:I186143895,publication_year:2016-2026&group_by=open_access.oa_status"
# exact type mix; also works for sustainable_development_goals.id, funders.id, publication_year
```

`validate_via_groupby.py` in this repo does exactly this and cross-checks the dashboard's figures
against live data in **7 calls**. Use `sample=N&seed=K` only when you need to *inspect records*
rather than count them; use cursor paging only to *collect* the corpus, never to measure it.

### Upstream changes this pipeline has to survive (Sept 2026)

Checked against this corpus; the numbers are what the checks actually returned.

| Change | Effect here | Handling |
|---|---|---|
| Work IDs merged/retired; mega-works split; ~2.7M figshare items no longer standalone | **23 of 409** no-DOI rows had dead links (5.6%) | `check_dead_ids.py` flags them; `pack.py` sets `gone`; the page shows the title unlinked with an explanation |
| OA reclassification — 742k Elsevier Open Archive works became free to read; false OA flags removed from ~511k footer-licence, 244k figshare, 49k OSTI, 55k Springer records | ~**500 works** moved between closed/green/bronze in one week; gold/hybrid/diamond stable | Documented on the page: bronze and closed are provisional |
| Funders migrating from Crossref Funder Registry to ROR; duplicate merges and retirements next | Only **1 duplicate pair** in 1,977 funder names, each used once | No action; expect funder names to consolidate on refresh |
| New cap (14 Sept): OR-ing >10 ids on `topics.id`, `primary_topic.id` or `concepts.id` → 1 req/sec, else `429` | **Not triggered** — no script filters on topic ids | If you add a topic filter, chunk id lists to ≤10 |

Two of these will recur, so `check_dead_ids.py` is part of the refresh recipe and the OA caveat is
permanent page copy rather than a one-off note.

### Get a free API key before the next refresh

**An API key is optional but free, and it raises the daily budget tenfold.** Metering is per call:
list-and-filter calls cost **$0.10 per 1,000**, single-entity gets are free, search is $1/1,000.
The budget is **$0.10/day with no key and $1.00/day with a free key**.

A full four-crawl rebuild of this dashboard was about **300 list calls ≈ $0.03 — roughly 30% of
the keyless daily budget**, and that is for an 11-year window. Widen the range to all 43,796
Lehigh works and one crawl alone is ~220 calls; four would be ~88% of the keyless budget and the
fifth would start returning `429`. Get a key, then pass it as `api_key=…` or as a bearer token in
the `Authorization` header.

Note there is **no mailto/polite-pool requirement** any more — identification is via the key, so
there is no reason to put anyone's email address in a query string.

### Reference

- [llms.txt](https://help.openalex.org/llms.txt) — machine-readable index of the whole help site;
  point an AI agent here first. (`developers.openalex.org/llms.txt` 301-redirects to it.)
- [API documentation](https://developers.openalex.org/) — start at *Analyzing your Institution*
  (this dashboard's exact use case), *Work Attributes* (the canonical field list for `SELECT`),
  *Group*, *Authentication* and *Deprecations*.
- [OpenAlex LLM quick reference](https://help.openalex.org/api/llm-quick-reference/) — concise,
  but thin: it documents `sample`/`seed` and the `grants` → `funders`/`awards` deprecation, and
  covers neither cursor pagination, publisher lineage, corresponding-author data, nor which
  fields are groupable.
- [github.com/ourresearch/openalex-guts](https://github.com/ourresearch/openalex-guts) — the
  code that computes the data; read it when the docs do not explain a field's behaviour.
  (`ourresearch/openalex-docs` is retired — the live docs source is `ourresearch/docs`.)
