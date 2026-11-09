#!/usr/bin/env python3
"""
Build a self-contained Swagger UI page from an OpenAPI spec.

Copy next to openapi.yaml, adjust TITLE/INTRO, run:
    python3 build-swagger-docs.py

Why the spec is embedded in the HTML instead of fetched:
opened over file://, Swagger UI cannot fetch a sibling openapi.yaml (CORS),
and shows only a resolver error. Embedding makes the file work on a
double-click, offline, with no server.

One-time vendor step (pin the major you tested against):
    mkdir -p vendor
    for f in swagger-ui.css swagger-ui-bundle.js swagger-ui-standalone-preset.js; do
      curl -sfL -o "vendor/$f" "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/$f"
    done
"""
import json
import pathlib

try:
    import yaml
except ImportError:
    raise SystemExit("Needs PyYAML: pip install pyyaml")

HERE = pathlib.Path(__file__).parent
SPEC = HERE / "openapi.yaml"
OUT = HERE / "index.html"

# --- customise -------------------------------------------------------------
TITLE = "<PROJECT> API — what the app needs from the backend"
INTRO = """
    Endpoints the client actually calls. <code>[custom]</code> = this project's
    own routes, <code>[framework]</code> = stock framework routes. Field-level
    contract and sync notes: <code><PROJECT>-DATA-CONTRACT.md</code>.
"""
# ---------------------------------------------------------------------------

spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))

# A literal </script> anywhere in the spec text would close the tag early and
# blank the page.
spec_json = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{TITLE}</title>
<link rel="stylesheet" href="vendor/swagger-ui.css">
<style>
  body {{ margin: 0; background: #fafafa; }}
  .bx-head {{
    background: #16141a; color: #fff; padding: 28px 24px 24px;
    font: 400 15px/1.5 -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  .bx-head h1 {{ margin: 0 0 8px; font-size: 24px; letter-spacing: -0.01em; }}
  .bx-head p {{ margin: 0; max-width: 70ch; color: #c9c4d1; }}
  .bx-head code {{ background: #2a262f; padding: 1px 5px; border-radius: 4px; font-size: 13px; }}
  .swagger-ui .topbar {{ display: none; }}
</style>
</head>
<body>
<div class="bx-head">
  <h1>{TITLE}</h1>
  <p>{INTRO}</p>
</div>
<div id="swagger-ui"></div>
<script src="vendor/swagger-ui-bundle.js"></script>
<script src="vendor/swagger-ui-standalone-preset.js"></script>
<script>
  window.ui = SwaggerUIBundle({{
    spec: {spec_json},
    dom_id: "#swagger-ui",
    deepLinking: true,
    docExpansion: "list",
    defaultModelsExpandDepth: 1,
    defaultModelExpandDepth: 4,
    // Reference doc, not a console: a dead request button invites the reader
    // to debug the doc instead of reading it.
    tryItOutEnabled: false,
    supportedSubmitMethods: [],
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
    layout: "BaseLayout",
  }});
</script>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")

ops = sum(
    1
    for p in spec["paths"].values()
    for m in p
    if m in ("get", "post", "put", "patch", "delete")
)
print(f"{OUT} — {len(spec['paths'])} paths, {ops} operations, "
      f"{len(spec.get('components', {}).get('schemas', {}))} schemas")
