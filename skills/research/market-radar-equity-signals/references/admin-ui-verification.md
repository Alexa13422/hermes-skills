# Verifying the admin UI (server-rendered inline JS)

The admin panel renders HTML/CSS/JS from Python triple-quoted strings in
`src/radar/admin_pages.py`. Python's import succeeding proves nothing about the embedded JS, and
there is no bundler or linter in the chain to catch a malformed script. One bad character takes
out **every** interactive feature on **every** page at once — no clicks, no drawers, no charts,
no graph — while the server still returns HTTP 200 and the page still renders its static markup.
HTTP status checks and "the service is active" therefore cannot detect it.

## The two failure modes, both seen in production

**Apostrophes in non-English prose inside single-quoted JS strings.** Ukrainian words like
`ім'я` and `зв'язки` contain an ASCII apostrophe that terminates the string literal early,
leaving the rest of the sentence as bare code. Backslash-escaping does not survive the Python
layer: inside a triple-quoted Python string, `\'` emits a literal backslash followed by a
quote, which is still a broken JS literal.

*Rule:* never put an ASCII `'` inside a single-quoted JS string in server-templated code — use
the typographic `’` (U+2019) in the prose, or switch that literal to double quotes.

**Missing block braces.** A `const` declaration directly after a brace-less `else if(...)` is
invalid JS. Minified one-liner style hides it from visual review.

*Rule:* give every `if`/`else if` branch explicit `{}` when it declares a binding.

## Verification recipe

Run a throwaway instance on a spare port so the user's live service is never interrupted. The
admin requires Telegram env vars and exits code 2 without them, so source `.env` first:

```bash
cd /home/alexa/programming/crypt/market-radar
set -a && . ./.env && set +a
<uv> run python -m radar --config config.toml admin --host 127.0.0.1 --port 8799
```

**1. Static syntax check of every page's inline script** (fast, catches the whole bug class):

```python
import re, urllib.request, os
pages = ['/', '/news', '/graph', '/signals', '/screening', '/prices',
         '/evaluation', '/proposals', '/logs', '/settings']
os.makedirs('/tmp/js', exist_ok=True)
for p in pages:
    html = urllib.request.urlopen('http://127.0.0.1:8799' + p).read().decode()
    for i, s in enumerate(re.findall(r'<script>(.*?)</script>', html, re.DOTALL)):
        open(f"/tmp/js/{(p.strip('/').replace('/', '_') or 'root')}_{i}.js", 'w').write(s)
```

Then `node --check` each extracted file. Also grep the source for the escape pattern that
cannot work: `grep -n "\\\\'" src/radar/admin_pages.py` must return nothing.

**2. Runtime check with a `pageerror` listener.** Visit all pages with Playwright
(`<uv> run --with playwright python ...`, `executable_path="/usr/bin/chromium"`,
`args=["--no-sandbox"]`) and assert the collected `pageerror` list is empty. A missing favicon
404 is noise, not a finding.

**3. Exercise the actual interaction**, do not infer it from markup — click a row and assert the
drawer really opened:

```python
await page.click("text=NVDA")
assert await page.evaluate("document.getElementById('drawer')?.classList.contains('open')")
```

**4. Verify gestures with real events and report before/after numbers.** Mouse wheel and
`page.mouse.down/move/up` cover desktop zoom and pan; two-finger pinch needs raw CDP:

```python
cdp = await page.context.new_cdp_session(page)
await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [
    {"x": cx - 30, "y": cy, "id": 1}, {"x": cx + 30, "y": cy, "id": 2}]})
# widen the gap over several touchMove frames, then touchEnd with touchPoints: []
```

Read a visible-state readout (e.g. the chart's summary line) before and after each gesture and
quote the concrete change — "1257 bars → 241 bars" is evidence; "pinch-zoom implemented" is not.
A mobile page needs `has_touch=True, is_mobile=True` for touch handlers to bind.

**5. Check mobile overflow** at 390×844: `document.documentElement.scrollWidth` must equal the
viewport width.

Kill the throwaway instance when done.
