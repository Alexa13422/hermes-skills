# Reading prices out of a JS-rendered shop catalog

Symptom: `web_extract` returns the brand's marketing copy and the cookie banner but zero products,
and the page markdown contains no price strings at all.

## The extractor

```js
(() => {
  const lines = (document.body.innerText||'').split('\n').map(s => s.trim());
  const out = [];
  for (let i = 0; i < lines.length - 2; i++) {
    if (/^[\d\s\u00a0]+,\d{2} zł$/.test(lines[i+2]) && lines[i] &&
        lines[i] === lines[i].toUpperCase() && lines[i].length > 2 && lines[i].length < 30) {
      out.push(lines[i+1] + ' — ' + lines[i+2]);
    }
  }
  return {count: out.length, items: [...new Set(out)]};
})()
```

Why this shape:

- **Triplet match (brand / name / price).** Product cards in these grids are wrapper `div`s; the
  anchor around a card often has no text node, so `a.innerText` filtered on a currency symbol returns
  an empty array while the prices are visibly on screen.
- **Upper-case brand-line guard.** Without it the same scan picks up filter sidebars, shipping
  thresholds and footer copy as products.
- **`\u00a0` in the digit class.** Locales print `1 349,00 zł` with a non-breaking space; `\s` alone
  misses it, so every four-digit (i.e. most expensive) item silently disappears.
- **Comma decimal.** Adapt the separator and currency token per locale rather than normalising the
  string first; normalising loses the row when the format is unexpected.

A brand-specific variant (`BRAND\n<name>\n<price>` via `RegExp`) works too, but the generic triplet
scan ports across brand pages unchanged, so prefer it.

## Writing the probe

Build the regex with `new RegExp('...', 'g')` when the expression is long — escaping a literal
`/.../g` through the JS-in-JSON hop is where the typos land, and a syntax error costs a whole
round trip. Return a small diagnostic object (`{len, hasBrand, count, items}`) rather than just the
list: when `len` is 0 the page has unmounted and the result is not "no products", it is "no page".

## Pagination

Do not scroll-then-collect. Re-navigate to the next page URL (or the `?page=N` form if the site has
one) and run the extractor per load. Deduplicate across loads with a `Set`.

## Reporting coverage

Compare parsed rows against the page's own "N products" line. When they disagree, state which brand
is partial and what categories did come through — in a truncated grid, discovery sets, sample kits
and candles tend to render before full-size bottles, which is useful information but is not the
flacon price that was asked for.
