---
name: retail-catalog-price-research
description: "Use when surveying a shop's catalog for products and prices."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [prices, retail, catalogs, scraping, recommendations]
    related_skills: [product-price-monitor, blocked-page-recovery, grounded-citations]
---

# Retail catalog price research

## When to Use

Use when the user names a shop and asks what it carries and what it costs — surveying a live catalog
across brands or categories, then recommending. Also when a first `web_extract` on a storefront
returns brand copy but no product rows.

Don't use for: watching one pinned item's price over time (`product-price-monitor`), or pricing
services in a city (`local-service-price-research`).

## Procedure

1. **Try the cheap route once.** `web_extract` on the brand/category page. If it returns marketing
   copy and the cookie banner but no product rows, the grid is client-side rendered — stop extracting
   and switch to the browser. Do not retry the same URL with a bigger `char_limit`.
2. **Harvest real URLs from a rendered page; never guess slugs.** The nav label and the live path
   routinely differ (a menu reading `/menu/marki` serving pages at `/menu-marka/<slug>`), and a 404
   from a guessed slug is indistinguishable from "this shop doesn't carry that brand".
   ```js
   (() => { const out = {};
     document.querySelectorAll('a[href]').forEach(a => { const h = a.getAttribute('href');
       if (h && /mark|brand|categor/i.test(h) && h.length < 90) out[h] = (a.textContent||'').trim(); });
     return Object.entries(out); })()
   ```
3. **Parse `document.body.innerText`, not anchor text.** Cards are usually wrapper `div`s whose link
   holds no text node, so collecting `a.innerText` filtered on a currency symbol returns an empty
   list while prices are plainly on screen. The flattened text keeps card fields as consecutive lines
   — brand (upper case), name, price — so match the triplet. See
   `references/js-rendered-catalogs.md` for the extractor and locale notes.
4. **Record the advertised count per page** ("31 products") and compare it to rows parsed. The gap is
   the thing you must report, not smooth over.
5. **Pull the shop's own thresholds** from the header/footer strip: free-sample tiers, free-shipping
   minimum, limited editions. They change the cheapest honest way to try an expensive item.
6. **Recommend concretely**, cheapest credible entry point first — for expensive goods, a sample or
   discovery set at a fraction of the full-size price beats a full-size pick, and say so with both
   numbers.

## Always-on rules

- **Never fill a rendering gap from model knowledge.** Quoting a price for a row that never rendered
   is the one error the user cannot detect from the answer. Name the brand that came back partial,
   list what did render, and offer to re-fetch it.
- **Prices are as-observed, with the source currency and format kept** (`1 349,00 zł`, not "about
   1350 PLN"). A catalog survey is a dated snapshot; do not present it as a standing price list.
- **When the user's framing of the shop or product category is wrong, correct it before answering**
   — agreeing with a wrong premise teaches a wrong model of what they are buying.
- **Group output by brand with a one-line reason each**, then a short "what I'd actually buy"
   verdict. Not a flat alphabetical dump of every row parsed.

## Pitfalls

- Scrolling to lazy-load the rest of a grid can leave the SPA with an empty
   `document.body.innerText`, losing rows already collected — re-navigate or request the next page
   URL and parse each load separately.
- Filter sidebars and shipping banners also contain numbers; without the upper-case brand-line test
   the extractor reports them as products.
- A locale price regex needs `\u00a0` for the thousands separator; `\s` alone silently misses every
   four-digit price, making expensive items vanish from the survey.
