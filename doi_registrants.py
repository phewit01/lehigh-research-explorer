"""DOI prefix -> Crossref registrant, used ONLY as a fallback when OpenAlex has
no source record for a work. Prefix ownership is stable and publicly documented,
so this is a lookup rather than a guess — but it is still derived, and the
dashboard marks it as such.

`conf` marks registrants whose DOI suffixes commonly carry a conference acronym,
so an acronym is only read from the suffix where that is meaningful.
"""

REGISTRANTS = {
    "10.1109": ("IEEE", True),
    "10.23919": ("IEEE", True),
    "10.1145": ("ACM", True),
    "10.18653": ("ACL", True),
    "10.24963": ("IJCAI", True),
    "10.14722": ("Internet Society", True),
    "10.1115": ("ASME", True),
    "10.18260": ("ASEE", True),
    "10.1061": ("ASCE", True),
    "10.2514": ("AIAA", True),
    "10.1117": ("SPIE", True),
    "10.4271": ("SAE International", True),
    "10.1190": ("SEG", True),
    "10.1149": ("Electrochemical Society", True),
    # Names below deliberately match the publisher buckets produced from
    # OpenAlex lineage, so a derived publisher lands in the same bar as a
    # recorded one instead of creating a near-duplicate.
    "10.1007": ("Springer Nature", False),
    "10.1038": ("Springer Nature", False),
    "10.1002": ("Wiley", False),
    "10.1111": ("Wiley", False),
    "10.1016": ("Elsevier BV", False),
    "10.1063": ("American Institute of Physics", False),
    "10.31235": ("SocArXiv", False),
    "10.31224": ("engrXiv", False),
    "10.36227": ("TechRxiv", False),
    "10.4324": ("Routledge", False),
    "10.17504": ("protocols.io", False),
    "10.1137": ("SIAM", False),
    "10.1142": ("World Scientific", False),
    "10.21468": ("SciPost", False),
    "10.1021": ("American Chemical Society", False),
    "10.1088": ("IOP Publishing", False),
    "10.1039": ("Royal Society of Chemistry", False),
    "10.1080": ("Taylor & Francis", False),
    "10.1201": ("CRC Press", False),
    "10.1093": ("Oxford University Press", False),
    "10.1017": ("Cambridge University Press", False),
    "10.1103": ("American Physical Society", False),
    "10.3390": ("MDPI", False),
    "10.1177": ("SAGE Publishing", False),
    "10.1108": ("Emerald", False),
    "10.1371": ("PLOS", False),
    "10.1126": ("AAAS", False),
    "10.1073": ("PNAS", False),
    "10.1136": ("BMJ", False),
    "10.1121": ("Acoustical Society of America", False),
    "10.1364": ("Optica", False),
    "10.1520": ("ASTM International", False),
    "10.3102": ("AERA", False),
    "10.5194": ("Copernicus", False),
    "10.1101": ("Cold Spring Harbor Laboratory", False),
    "10.21105": ("Journal of Open Source Software", False),
    "10.2172": ("US Department of Energy (OSTI)", False),
    "10.22541": ("Authorea", False),
    "10.31234": ("PsyArXiv", False),
    "10.31219": ("OSF Preprints", False),
    "10.5281": ("Zenodo", False),
    "10.1287": ("INFORMS", False),
    "10.1061": ("ASCE", True),
    "10.1029": ("AGU", False),
    "10.1046": ("Wiley", False),
    "10.1099": ("Microbiology Society", False),
    "10.1152": ("American Physiological Society", False),
    "10.1161": ("American Heart Association", False),
    "10.1182": ("American Society of Hematology", False),
    "10.1210": ("Endocrine Society", False),
    "10.1242": ("Company of Biologists", False),
    "10.1289": ("NIEHS", False),
    "10.1359": ("ASBMR", False),
    "10.2139": ("SSRN", False),
    "10.3389": ("Frontiers", False),
    "10.7554": ("eLife", False),
    "10.1021": ("American Chemical Society", False),
}

if __name__ == "__main__":
    import json
    from collections import Counter
    works = json.load(open("works.json", encoding="utf-8"))
    nosrc = [w for w in works if not (w.get("src") or "").strip() and w.get("doi")]
    hit = [w for w in nosrc if w["doi"].split("/")[0] in REGISTRANTS]
    miss = Counter(w["doi"].split("/")[0] for w in nosrc
                   if w["doi"].split("/")[0] not in REGISTRANTS)
    print(f"source-less works with a DOI : {len(nosrc)}")
    print(f"  prefix recognised          : {len(hit)}  ({len(hit)/len(nosrc)*100:.1f}%)")
    print(f"  prefix unrecognised        : {len(nosrc)-len(hit)}"
          f"  ({len(miss)} distinct prefixes)")
    print("\nlargest unrecognised prefixes:")
    for p, c in miss.most_common(12):
        print(f"  {c:4d}  {p}")
