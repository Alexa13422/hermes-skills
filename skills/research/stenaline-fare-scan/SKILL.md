---
name: stenaline-fare-scan
description: Scan Stena Line fares/promo codes via booking GraphQL.
---

# Stena Line fare / promo scanning

Use when checking Stena Line ferry prices, promo-code availability (e.g. Gdynia–Karlskrona "100 zł" jubilee offer), or scanning many sailing dates at once.

The public pages render nothing useful server-side. The booking funnel `book.stenaline.pl` is a SPA talking to a single endpoint `POST https://book.stenaline.pl/graphql`. Scan it from the browser console after bootstrapping a real session — anonymous curl to /graphql has no session, and the SPA bundles carry no API docs.

## Workflow

1. Find the promo's offer code + product code in the marketing page HTML (e.g. `https://www.stenaline.pl/oferty-specjalne/100lat-gdyni`):
   - `curl -sL <offer-page>` then grep `offer-code__offer-code-input` → `value="GDYNIA100"`,
     `name="product-code"` → `CRUSKG2C`, `name="sales-owner-code"` → `16`.
   - Route codes live in the `<option value="GDKA">Gdynia → Karlskrona</option>` selects.
2. Enter the funnel directly (skips the search widget):
   `https://book.stenaline.pl/redirect?routeOut=GDKA&routeHome=KAGD&depDateOut=2026-10-08&depDateHome=2026-10-09&offercode=GDYNIA100&hideOfferCode=1&product=CRUSKG2C`
   Accept the OneTrust cookie banner, set passengers and "Pieszo", continue — this creates the `bookingSessionId` and applies the offer code.
3. Scan dates with `searchRoundTripPairs` (exact query + variables in references/graphql.md).

## Pitfalls

- **Product code differs between widget and API.** The marketing page's `CRUSKG2C` returns `SearchRoundTripPairsNotFound` for every date. The real sailing-product codes are `CRUSKG1` ("Rejs 24h") and `CRUSKG2` ("Rejs 36h"). Always try both; unknown codes return `SearchRoundTripPairsError`.
- **`offerCodeStatus` is not a reliable signal.** A deliberately bogus code also returns `OfferCodeStatusSoldOut`. Judge the promo by `packagePricing`: `RoundTripDiscountedPrice` (with priceBefore/After) = promo applied, `RoundTripUndiscountedPrice` = regular fare. `totalPrice.amount` covers ALL passengers, in PLN.
- **`soldOut: true` ⇒ `totalPrice: null`.** Filter those out before reporting a "cheapest".
- **browser_console times out on long loops.** Never `await` a 60-date scan inside the evaluated expression. Start an async IIFE writing into `window.__scan` + `window.__done`, return immediately, `sleep 70` in the terminal, then read results in a second call.
- **GraphQL field args are mandatory and undocumented.** `sailingProduct.name` needs both `languageId` and `salesChannelCode: "PIB"`. Drop optional subfields rather than fight the schema.
- Capture real queries by monkey-patching `window.fetch` into `window.__log` before clicking through, then trim the operation. Slice response bodies before returning them.
- Chromium on a 4 GB Pi: if `browser_navigate` fails with `CDP command timed out: Page.enable`, kill stale `chromium` / `chrome-linux` PIDs and retry.

## Monitoring

Delivery runs through a systemd **user timer**, not the Hermes cron job:
`~/.config/systemd/user/stena-monitor.{service,timer}` (every 15 min, `Persistent=true`,
needs `loginctl enable-linger`) calling `~/.hermes/scripts/stena_notify.sh`, which pipes
the monitor's stdout to the Telegram Bot API. Verify a change end-to-end by raising
`ALERT_TOTAL` to force an alert, running the notify script, then restoring the threshold.


Once the operation is captured, the query works with plain `curl`/`urllib` from the
shell — no browser session or cookie needed, just `Origin`/`Referer`/`User-Agent`
headers pointing at book.stenaline.pl. That makes it cheap to cron.

Ready-made monitor: `~/.hermes/scripts/stena_promo_monitor.py` (2 adults,
GDKA, 08.10–11.12 window). Tunables at the top: `PRODUCTS`, `NIGHT_FROM`,
`ALERT_TOTAL`, `PROMO_TARGET_TOTAL`. Narrowing the product set and filtering to
night-out/night-back pairs cuts a full scan from ~2.5 min / 130 requests to
~1.2 min / 65. Run it as a `no_agent` cron job with `script=stena_promo_monitor.py`:
it keeps state in `~/.hermes/state/stena_promo_monitor.json`, prints to stdout ONLY
when the promo returns, a fare lands under the alert threshold, or the minimum
drops — and writes quiet runs to stderr so the watchdog delivers nothing.
