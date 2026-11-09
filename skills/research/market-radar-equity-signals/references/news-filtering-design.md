# News filtering design

Goal: ingest the entire world news stream, keep only graph-relevant items, and spend LLM calls
only on plausible events — while retaining enough record to backtest every decision later.

## Why bulk files, not a search API

Per-company queries against the GDELT DOC API hit server-side `429 Too Many Requests` and there
is no paid tier to raise it. Instead pull the GKG 2.0 bulk feed: read
`https://data.gdeltproject.org/gdeltv2/lastupdate.txt`, download the 15-minute
`.gkg.csv.zip` it names, and match locally. Two requests cover all global news for the window
regardless of watchlist size.

- `lastupdate.txt` hands back an `http://` URL that redirects to HTTPS. The project's httpx
  client defaults to `follow_redirects=False`, which yields zero rows and an opaque error
  count — pass `follow_redirects=True` on that GET.
- GKG carries metadata only: organizations, persons, themes, tone, URL, and sometimes short
  `Quotations` fragments. There is no article body and no ready-made summary, so titles are
  fetched per matched row and capped by `max_title_fetches`.
- A diagnostic run that reports `rows: 0, errors: 1` is a fetch/parse failure, not a quiet news
  day — check the download before touching the matching logic.

## Titles: the URL fallback is a hot path, not an edge case

The `<title>` fetch is capped per cycle (`max_title_fetches`), so every matched row past that
budget gets its title derived from the URL. Treat that fallback as production quality, not a
last resort.

Derive it by walking path segments from the END and skipping ID-like ones — bare digits,
timestamps, and `article`/`story`/`post`/`id` prefixes. Many publishers put the readable slug in
the second-to-last segment and a bare article id last
(`.../why-big-tech-is-giving-away-open-weight-ai-models/article71596411.ece`), so taking only the
final segment yields `article71596411` as the headline. Fall back to the domain only when no
segment is readable, and never let an id through as a title.

A junk title is not cosmetic: it is the text the LLM stages and the owner both read, so a row
titled `article71602841` or `www.wlky.com` can reach a signal with nothing to judge it by.

When fixing a derivation bug like this, scope the damage with a pattern query over the whole
table before trusting the count in the one example reported — searching only for the shape the
user quoted found 5 rows, while `title GLOB 'article[0-9]*' OR title GLOB 'www.*' OR title GLOB
'*.com'` found 83. Repair stored rows by re-running the real resolver (`resolve_title()`) over
them rather than re-deriving from the URL; the live `<title>` is better than any slug.

## Gate 1 — match confidence (entity false positives)

Short company names collide with ordinary words and surnames: an article about an actor named
Ford matched the Ford Motor node, because the matcher searched organizations, persons, and
themes as one concatenated blob.

Do **not** solve this by deleting short tokens from the vocabulary — that silently drops real
coverage, since genuine coverage often names a company in one word. Instead exploit the field
provenance GDELT already provides and score each match:

- **high** — match landed in the Organizations field, or the matched phrase is multi-word, or it
  is a ticker symbol, or the source is a direct `sec:<ticker>` feed.
- **low** — a single-word match appearing **only** in the Persons field.

An item whose matches are all low-confidence is filtered before significance with reason
`low_confidence_match`; one high-confidence match lets the item proceed on that asset. Both the
full match list and the low-confidence subset persist, so the audit row still shows the match
was seen.

General rule: when upstream data already distinguishes entity types, gate on that provenance
rather than editing your own dictionary. Other watchlist names carrying the same risk are
ordinary words or surnames — apple, nike, delta, micron, deere, tesla, caterpillar, boeing.

## Gate 2 — deterministic significance

A cheap tone/theme test runs before any LLM call. It passes on any one of:

- `|tone| >= TONE_THRESHOLD` (5.0; GKG tone runs roughly -10..+10),
- a theme in `ALARMING_THEMES` (bankruptcy, trade dispute/tariff, sanctions, antitrust,
  cyberattack, industrial accident, IPO, …),
- **repetition** — the same normalized title from `>= 3` distinct domains inside a 6h window,
- **earnings-title override** — an explicit profit/earnings headline pattern.

The last two exist because GDELT's own classifier is unreliable on exactly the items that matter
most: a "sixth straight record profit" story carried `tone = 0.23` and no earnings theme, so
tone-and-theme alone discarded it. Wide syndication is itself an importance signal, and a
headline regex catches what the classifier missed.

When adding a headline regex, use word boundaries so `profit` cannot match inside `nonprofit`.
When adding a theme, skip the very frequent generic buckets (`CRISISLEX_*`, `EPU_POLICY*`,
`TAX_FNCACT*`) — they pass essentially everything.

Sources without GKG data (SEC EDGAR, FRED) must bypass this gate entirely; it has no tone or
themes to judge them by.

## Audit trail

Every decision records *why*: the significance trigger that fired (`tone` / `theme` /
`repetition` / `earnings_title`, plus `domain_count` for repetition) goes into the screening
decision details, and the full match list plus confidence lands on the news row. This is what
makes the stored corpus replayable for backtests and lets the admin explain a verdict in words
instead of dumping fields. Store the structured match list separately from "which assets were
actually alerted" — they are different questions and conflating them loses backtest coverage
when one article matches several companies.

## Expected volumes

A 15-minute window is roughly 550 rows, of which ~30 match the graph. Conservative thresholds
mean whole batches can legitimately produce zero significance passes; that is tuning, not a
breakage. Treat a *sustained* zero-signal stretch as the trigger to revisit thresholds.

## Evaluation emptiness

The evaluation page scores *generated signals* against later price moves. When screening emits
no signals, evaluation is correctly empty — look upstream at the gates rather than debugging
evaluation itself.
