# Sourcing an image asset that can ship inside an app

## Licence filter

- **CC0 and public domain only** for anything bundled into a closed application.
- **Reject CC BY-SA**: share-alike can reach the work the asset is embedded in,
  and attribution must then be rendered somewhere in the UI. A search for "free"
  images returns these first, so the licence must be filtered, not assumed.
- CC BY is sometimes acceptable but still forces an attribution surface — decide
  that with the user before building it in.
- General stock sites (Pexels, Pixabay, Unsplash, clipart hosts) carry
  site-specific terms that are neither machine-readable nor uniform per file.
  Prefer a source that exposes the per-file licence through an API.

## Wikimedia Commons, programmatically

Endpoint `https://commons.wikimedia.org/w/api.php`, with a descriptive
`User-Agent` header (requests without one get throttled).

- Search: `action=query&list=search&srnamespace=6`, query like
  `filetype:bitmap cumulus cloud blue sky`.
- Restrict to free files at search time with structured-data statements:
  - `haswbstatement:P6216=Q19652` — copyright status: public domain
  - `haswbstatement:P275=Q6938433` — licence: CC0
- Metadata: `prop=imageinfo&iiprop=url|extmetadata|size&iiurlwidth=1800`.
  Check `extmetadata.LicenseShortName` against an allow-list of `cc0`,
  `public domain`, `pd-`, `pdm`; record `Artist` and the file page URL in a
  manifest next to the downloads.
- Filter on `width`/`height` from the same call (minimum width, landscape) before
  downloading, and build a contact sheet of the survivors for one visual pass —
  searches for an isolated subject return satellite imagery and wide landscapes
  that no licence check will catch.

## Pitfall

A photographic asset resists layer-based animation: it cannot be sliced into
depth layers that hold up when they move at different speeds. If the design calls
for parallax churn, procedural layers with independent alpha beat a photo, and
that tradeoff belongs in front of the user as an explicit choice rather than being
settled silently.
