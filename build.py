"""Splice payload.json into template.html and emit both delivery formats.

  lehigh-research-explorer.html   Claude Artifact — the host wraps the file in its
                                  own doctype/head, so no document scaffolding here.
  lehigh-dashboard/index.html     Standalone for GitHub Pages or any web server —
                                  needs a full document, charset and viewport of
                                  its own, plus the small reset the Artifact host
                                  would otherwise provide.
"""
import io
import os

tpl = io.open("template.html", encoding="utf-8").read()
data = io.open("payload.json", encoding="utf-8").read()
# Escaping '<' keeps a stray "</script>" inside any title from closing the block.
data = data.replace("<", "\\u003c")
assert "/*__DATA__*/" in tpl
body = tpl.replace("/*__DATA__*/", data)

io.open("lehigh-research-explorer.html", "w", encoding="utf-8").write(body)

STANDALONE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Filterable dashboard of Lehigh University affiliated research output, 2016-2026, from OpenAlex.">
<style>
  :root { color-scheme: light; }
  body { margin: 0; }
  img { max-width: 100%; }
  [hidden] { display: none !important; }
</style>
</head>
<body>
"""

os.makedirs("lehigh-dashboard", exist_ok=True)
io.open(os.path.join("lehigh-dashboard", "index.html"), "w", encoding="utf-8").write(
    STANDALONE_HEAD + body + "\n</body>\n</html>\n")

print("artifact  :", len(body.encode("utf-8")), "bytes")
print("standalone: lehigh-dashboard/index.html")
