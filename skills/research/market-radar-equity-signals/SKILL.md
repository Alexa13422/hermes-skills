---
name: market-radar-equity-signals
description: "Market Radar equity signals: pipeline, admin UI, deploy."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [market-radar, equities, news-pipeline, sqlite, raspberry-pi, admin-ui]
    related_skills: [raspberry-pi-operations, systematic-debugging]
---

# Market Radar — Equity Signal Pipeline

Personal single-host attention-signal system: collect world news, match it against a graph of
companies/industries/macro nodes, filter cheaply before any LLM call, emit attention scores 1-5
(never buy/sell advice), and evaluate them against real price history.

## When to Use

- Any work inside `/home/alexa/programming/crypt/market-radar`.
- Changing the news collector, entity matching, significance gates, screening, signals, or
  evaluation.
- Editing the admin panel at `127.0.0.1:8787` or its remote Tailscale Serve URL.
- Backfilling or inspecting price history, or debugging "why was this news filtered / why is
  evaluation empty".
- Restarting, migrating, or verifying `market-radar.service` / `market-radar-admin.service`.

## Environment

- Project: `/home/alexa/programming/crypt/market-radar`, branch `main`.
- `uv` is NOT on PATH — always `/home/alexa/.hermes/tools/uv-0.12.3-linux-arm64/uv`.
- Tests are **unittest**, not pytest, despite pyproject's pytest block:
  `<uv> run python -m unittest discover -s tests`
- `sqlite3` CLI is not installed. Query the DB through Python:
  `<uv> run python -c "import sqlite3; c=sqlite3.connect('data/radar.sqlite3'); ..."`
- Table names do not match the domain words: news lives in **`news_items`** (not `news`),
  prices in **`price_bars`** (not `prices`), and evaluations in `signal_evaluations`. List
  `sqlite_master` first rather than guessing — a wrong guess aborts the whole script mid-query
  and wastes the round trip:
  `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`
- Services: `market-radar.service` (collector) and `market-radar-admin.service`
  (admin, `127.0.0.1:8787`). Remote access is `tailscale serve` →
  `https://pi-4.tail4a834d.ts.net/`.
- `config.toml` and `.env` are gitignored and local. Never commit them, never print their
  contents.

## Always-on rules

- **Admin stays loopback-only.** It has no application auth, so binding it to `0.0.0.0` or the
  Tailscale IP would expose unauthenticated POST controls — route external access through
  `tailscale serve` instead. The Serve hostname is stable across restarts; if it looks dead,
  check whether Tailscale itself went offline before assuming the service failed.
- **Never touch NordVPN.** The user manages it manually and has explicitly forbidden
  enable/disable/connect/disconnect. A manual NordVPN connection can knock Tailscale offline —
  report that as the cause, do not "fix" it.
- **Never blind `git add -A`.** Stage explicitly (`git add -A -- src/radar/ tests/`) and read
  `git status --short` before committing, because ignored local config and scratch DBs sit in
  the same tree.
- **Never edit an already-applied migration.** Schema changes are a new `src/radar/migrations/0NN_*.sql`.
- **Signals are attention scores, not trading advice.** Preserve that framing in any copy,
  rule, or alert body you add.
- **Never purge news, screening decisions, signals, or evaluations.** The whole point of the
  stored history is future backtests; filtered-out items stay as audit rows.
- Minimal narration while working: no step-by-step commentary, just the important findings and
  a short final result.

## Procedure — shipping a change

### 1. Write a ticket, delegate, then verify yourself

Write the ticket to `/tmp/<topic>_ticket.md` and run
`agent coder -f /tmp/<topic>_ticket.md "Виконай інструкцію з прикладеного файлу."` in the
background. Always instruct the agent: do NOT commit, leave changes in the working tree, and
report which files it touched.

A coding agent's final report is a self-report, not a verified fact. Independently re-run the
full suite, read `git status --short` and `git diff`, and exercise the actual UI before
believing "done" — an agent reported success in the same session it introduced a JS
SyntaxError that broke every admin page.

Put a **"verified facts to build on (do not re-derive)"** section in every ticket, holding the
measurements you already took — URL formats that work, per-item timing, row counts, which
columns exist. Without it the agent re-measures from scratch, or worse, guesses and builds on
the guess.

For any job whose cost scales with a range (a backfill, a bulk fetch, a full-history rescore),
the ticket must name an explicit **STOP point** after a bounded pilot, and require the report to
be numbers read out of the DB. An agent handed an open-ended range will run the whole thing and
report estimates as results.

If the agent process dies (SIGTERM) mid-run, inspect `git status --short` and `git diff --stat`
before relaunching: the work is often substantially complete, and a from-scratch rerun throws
it away. Continue from the existing tree instead.

### 2. Verify admin UI changes without disturbing the live service

See `references/admin-ui-verification.md` for the full recipe. Non-negotiable core: extract the
inline `<script>` blocks from every page and run `node --check` on each, because this app's JS
lives inside Python triple-quoted strings where one bad character silently invalidates the
entire script.

### 3. Run the suite, then commit

```
<uv> run python -m unittest discover -s tests
```

Commit with a body that states what changed and the verified test count.

### 4. Apply migrations to the live DB and restart

Only when the change added a migration:

```
sudo systemctl stop market-radar.service market-radar-admin.service
<uv> run python -c "
from pathlib import Path
from importlib.resources import files
from radar.storage import Storage
s = Storage(Path('data/radar.sqlite3'))
s.migrate(files('radar').joinpath('migrations'))"
sudo systemctl start market-radar.service market-radar-admin.service
```

`Storage` takes a `Path`, not a `str`, and migrations resolve through
`files('radar').joinpath('migrations')`. Changing only Python/JS needs just
`sudo systemctl restart`, no migrate step. Editing a file on disk does nothing until the unit
restarts — a stale process is the usual reason a verified fix appears absent in the browser.

Confirm after restart: `systemctl status ... --no-pager`, `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/`,
and `sudo tailscale serve status`.

### 5. Migrations do not backfill

A new column lands empty on existing rows, so a newly added signal only applies to data
collected from then on. Say so explicitly rather than implying the fix retroactively
reclassifies history; do not rewrite old rows to make a demo look better.

## News filtering pipeline

Stages, in order: GDELT GKG bulk file → local graph/entity match → match-confidence gate →
deterministic significance gate → LLM screening → graph propagation/signals/evaluation.
Irrelevant rows are discarded without a DB write; everything that matches is persisted with its
screening decisions.

Design rules and the tuning knobs are in `references/news-filtering-design.md`. Read it before
changing any threshold or adding a gate. It also covers title derivation, whose URL fallback is
a hot path because the `<title>` fetch is capped per cycle.

When the owner asks "why is this parsed like that?" about a stored field, find the code path
that produced it before explaining the data — the answer is usually a budget-capped fallback or
a gate, and guessing from the value alone misattributes the cause.

## LLM stages via OmniRoute: two silent killers

Both LLM stages call OmniRoute. Two traps make them fail with NO visible error — the log just
repeats `unavailable: 1` or `parse_error` and the signals table stays empty forever:

1. **Combo `responseValidation.minContentLength`** (120 on `claude-smart`, `codex-smart`,
   `code-pipeline`). Screening asks for compact JSON like `{"relevant":true}`, far under 120
   chars, so the combo rejects every 200 as low quality, burns all its models and returns
   HTTP 502. Point `model` at a **direct provider id** (`claude/claude-sonnet-5`) to bypass
   combo validation. Unprefixed names like `claude-opus` are invalid too — `/v1/models` lists
   only combos, so a bare id 400s with "Unable to determine provider".
2. **Thinking tokens eat the whole output budget.** Claude spends
   `completion_tokens_details.reasoning_tokens` before emitting content; Sonnet consumed a
   2500-token budget and returned `finish_reason=length` with an EMPTY content string. Prefix
   schema-constrained stages with **`no-think/`** and keep `max_output_tokens` generous (4000).

Verify any model id with a live request before trusting config, and check BOTH `finish_reason`
and `len(content)` — a 200 with empty content is the failure mode to look for.

Distinguish truncation from schema violation when recording a parse failure: `finish_reason ==
"length"` is a budget problem, not a model that cannot follow the contract. Logging them
identically sends you tuning the prompt while the real fix is the token cap.

Model split the owner chose: a cheap model screens (Stage 2 `haiku`) and **Sonnet** does Stage 3 —
by then the earlier stages have parsed and narrowed the input, so the final reasoning step does
not need Opus. Keep `no-think/` on both.

## The reaction bonus must require a closed session

`adjust_score()` grants +1 when the tape is flat ("the market ignored it"). For news published
after the last close — weekends, holidays, intraday — `price_at_news` and `price_now` resolve to
the SAME bar, so the move is `0.0` by construction, not because the market shrugged. Without a
guard every signal collects the bonus and the output is a uniform 5/5 wall that looks confident
and means nothing. Gate it on `bars_since_news > 0` (sessions closed strictly after the news
day) and report `state=awaiting_session` otherwise.

**A uniform score distribution is the symptom to watch for.** If every signal lands on the same
score, the scoring is not discriminating — investigate before believing the output.

When a test encodes the buggy behaviour (asserting `state == "flat"` on a same-bar scenario),
rewrite the test to a scenario that genuinely exercises the rule rather than loosening the fix.

## Historical GDELT backfill

The live collector reads only `lastupdate.txt` (newest 15-minute slice), so the DB holds no
history and nothing is measurable. Historical GKG files are addressable directly by timestamp:
`https://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip`, slices at :00/:15/:30/:45.
Must be **https** with redirects followed — plain http returns 301 and an empty body that
`zipfile` then reports as "not a zip file", which looks like a parse bug.

Measured: ~4.9 MB zip, ~1218 rows, 0.24 s CPU, ~1.3 s download per file, ~6% match rate. One
hourly slice over 5 years = 43800 files, ~210 GB, ~2.9 h CPU. Never store the zips; stream, parse,
keep matched rows, discard bytes.

Do **not** fetch titles during backfill — `resolve_title()` is one live HTTP GET per row. Use
`_slug_title(url)`.

No LLM calls in backfill or backtest: a 5-year sample is millions of candidate rows, and the score
must be deterministic code anyway for the measurement to mean anything.

Required properties, each of which was initially missing and caught by cross-vendor review:

- A 404 must not be final. GDELT's archive has transient holes; count attempts and only mark a
  slice `gone` after several misses, otherwise a long run accumulates permanent silent gaps.
- Key history rows on `(url, file_ms)`, not `url` alone. `UNIQUE(url)` + `INSERT OR IGNORE` drops
  the same URL seen in another slice with different `matched_assets`.
- A valid zip whose entries contain no `*.gkg.csv` is an **error**, not an empty `ok` — otherwise
  the slice is never retried and its news is lost without a trace.
- The backfill script must exit non-zero when errors occurred, or automation treats a partial run
  as complete.

For a multi-hour resumable run, launch as a tracked persistent background process with a log and completion notification. On a status request, check both the worker PID and latest progress line, then compute `remaining / observed slices-per-second`; label the ETA as an estimate, not a deadline. Compare ledger counts by status (`ok`, `error`, `missing`, `gone`) with the log: progress within the requested range is not the cumulative ledger total when prior slices exist. A running process with `error`/`missing` is not a clean finished backfill; inspect and retry those slices after the main pass before claiming complete coverage. Check RAM/swap using the raspberry-pi-operations skill before changing concurrency—swap utilization alone is not an accelerator.

## Backtesting needs news older than a close

Forward returns are unmeasurable while every news item is newer than the newest price bar — the
normal state right after a fresh GKG collection. `scripts/backtest.py` resolves `matched_assets`
**graph node names** (`nvidia`) to tickers (`NVDA`) through `load_graph('graph/seed.yaml')`; a
plain `.upper()` matches nothing and silently yields zero events. Keep its explicit "no backtest
possible yet" verdict plus the pipeline-consistency report: a backtest that invents statistics
from an empty sample is worse than none.

## Measuring predictive power: four traps, in the order they bite

Every one of these produced a confident false "we found signal" in this project. Apply all four
before believing any number.

**1. Observation unit.** NVDA alone yields ~29k news rows per quarter, so event-level statistics
measure NVDA, not the algorithm. Aggregate to **ticker-day**. The same data gave mean −0.135% at
event level and +0.349% at ticker-day level — opposite signs.

**2. Beta.** Subtracting the benchmark 1-for-1 silently assumes beta = 1. Real estimates here:
MU 3.23, AMD 3.05, AMAT 2.67, TSLA 2.00, NVDA 1.85. On a rising market a naive SPY subtraction
leaves a large positive residual for every high-beta name, which looks exactly like signal. Use a
market model: OLS alpha/beta over a 120-day estimation window ending GAP=5 days **before** the
event (so the event cannot contaminate its own beta), then AR = actual − (alpha + beta·bench).

**3. Benchmark choice separates company from sector.** Coverage spikes measured against SPY gave
t = −4.15; the same spikes against the ticker's **sector ETF** gave t = −1.32. What looked like a
company signal was the sector moving. Always report both.

**4. Train/test split by date.** This is the one that kills everything else. Five features passed
|t|>2 with |mono|>0.8 on the full sample; none survived a split at 2026-08-01. `spike -> stock-car`
at h=5: t = −3.50 on train, **+0.59 on test**. Sign flips are the signature of overfitting.

Diagnostic for a pooled artefact: if `ALL` has a higher |t| than every individual bucket, the
effect is a common shift (market regime, beta) rather than discrimination by the feature. Same if
`all` is stronger than both of its own halves — that effect was created by concatenating regimes.

Normalise moves to **z = CAR / (idio_vol · sqrt(days))** using the estimation-window residual std.
Raw percent is not comparable across names: 4% is a quiet day for MU (idio vol 4.6%/day) and a
major event for WMT.

Acceptance rule used here: a cell counts only if |t| > 2 **and** |mono| > 0.8 **and** it holds on
`test`. Record rejected hypotheses in `EXPERIMENTS.md` with the same methodology as accepted ones —
the log of what does NOT work is what stops you re-testing it.

Run the sweep as a cross-product (`scripts/experiment_sweep.py`: feature × target × horizon ×
split) and judge cells only against each other, never one measurement in isolation. Rank
candidates by their **weaker half**, never by the pooled figure: `novelty -> stock-absz` scored
t=−7.71 on the full sample, the largest |t| in the table, while its own train half was t=−0.46.

The original 252-cell sweep used calendar dates for all news, including after-close reports; this is lookahead. Under a subsequent strict after-close shift, `macro -> stock-idio` h=21 fell below the train threshold (t −1.86; test −2.25). Do not call it validated. `relvol -> stock-absz` h=1 held (train t +3.85, test +2.80), but even that does not establish incremental forecast value or independent observations. A failed interaction feature does NOT establish independence of the components. The sweep's stated acceptance requires |t|>2 AND |mono|>0.8 on test; relvol test monotonicity +0.30 fails that criterion. Never describe it as a validated survivor.

Event time is more subtle than shifting dates: a post-close article can only use already-observed volume, not the NEXT day's volume. The sweep's shift alone still leaks next-session volume into post-close events. For a forecast made after today's close, use only articles available by that close and today's known OHLCV; post-close stories require a separate forecast protocol. US cash close moves with DST (20:00 UTC EDT, 21:00 UTC EST); use an exchange calendar, not a constant UTC cutoff. Weekends/holidays also need a trading calendar. GKG slice timestamps may indicate ingestion rather than article publication; verify provenance before claiming timing precision.

The volume-volatility relation can merely reflect volatility clustering. Before accepting volume, compare a baseline using today's absolute abnormal return to a nested model adding log(relative volume), and report incremental out-of-sample loss/R² on truly later dates. A pilot nested regression on news ticker-days (2017 observations, pre/post 2026-08 split) found baseline OOS R² +0.0300 vs +0.0360 with daily volume; M3 train volume t +3.90, but naive iid standard errors understate dependence from overlapping ticker-days and market-wide shocks. Also compare all trading days (volume alone), per-ticker and date-clustered uncertainty, and a rolling baseline; do not call a 0.006 OOS R² gain a product edge.

Continue hypothesis validation through its stated acceptance gates after a data backfill; a completed script run or unit suite is not a completed financial evaluation. Keep the next checks running or explicitly say that work is paused—do not imply an unattended evaluation continues when no process is active. Report verified results, failed gates, and outstanding checks separately, and obtain an independent methodological audit before promoting a signal.

Use annual walk-forward folds fitted only on earlier dates, but label a retrospective fold as robustness—not independent confirmation—if any of its data influenced feature selection. Align GKG timestamps in `America/New_York` and actual trading dates; for a forecast made after today's close, today's full-day volume is available, but never use next-session volume for a post-close story. Check early closes and verify whether the GKG timestamp is publication or ingestion time before asserting precise event timing.

Compare a volume-plus-volatility model against today's-volatility-only baseline **and against the same model on all trading days**. If volume works equally well without a news gate, treat it as a generic market feature, not a news-radar edge; test the incremental news interaction on matched ticker-days before attributing causality. Quantify missing archive slices by year and rerun sensitivity with sparse years excluded. Test ticker concentration, use date/ticker-clustered or block-bootstrap uncertainty rather than iid t-statistics, and benchmark against a stronger rolling volatility model. Do not equate a forecast of larger moves with profitable trades after spread/slippage. Small caps need separate liquidity- and size-stratified validation; do not extrapolate from large-cap results.

Published comparator: Anatolyev & Ponomarev, 'Does trading volume help forecast volatility?' (https://pages.nes.ru/sanatoly/Papers/VolVol.pdf): one-day OOS improvement from weekly/monthly volume lags on top of HAR realized volatility, little benefit at longer horizons; their intraday realized volatility and 41 DOW30 assets differ from this project's daily close proxy. Literature motivates testing, not confirmation. Record rejected hypotheses and corrections in `EXPERIMENTS.md`.

Everything else — GDELT tone, coverage volume (`spike`), domain novelty, daily high-low range — is
null out-of-sample at stock and sector level, for direction and for volatility. Do not re-test
these without a new data axis; the untested ones are intraday prices, earnings dates, and the
headline text itself (GDELT tone is a coarse aggregate of it).

Yahoo's chart API (`YAHOO_URL` in `prices.py`) already returns open/high/low/close/**volume** —
the `yfinance` package is not installed and is not needed. `price_bars` stored only `close`, so
volume-based features required a migration, not a new data source. When backfilling OHLCV onto
existing rows, upsert the new columns through `COALESCE(excluded.x, price_bars.x)` so a row
missing a field cannot blank out data already stored.

This is structural, not a passing phase: the live collector reads only the newest 15-minute GKG
slice, so history never accumulates backwards and waiting does not create a sample. Building one
means fetching historical slices by timestamp — procedure, measured costs, job-safety rules and
the LLM-free scoring requirement are in
`references/historical-backfill-and-backtest.md`.

**Measure the sample before answering any "how accurate is it" question.** Count how many
signals have at least one closed session after their news (query in that reference) and say the
number. When the owner asks for better prediction, the first deliverable is that count plus the
cost projection for the data needed — not a tuned threshold on an unmeasurable set.

## The structural score cannot see whether anything happened

The chain score measures the strength of the graph EDGE only. A politician praising an
*existing* tariff traverses the same critical `steel_tariff -> STLD` edge as a newly imposed
tariff, so it scored identically — and with a 97%-US-revenue geo bonus stacked on a tone of
-1.2 it shipped as 5/5. Structure alone is not materiality.

`significance.material_penalty()` supplies the missing axis deterministically, without asking
the LLM to judge: `COMMENTARY_THEMES` (political talk) with no `ACTIONABLE_THEMES` and no
earnings headline → -2; `|tone| < TONE_WEAK_THRESHOLD` → -1. Crucially, the `high_geo_exposure`
bonus must NOT stack on a penalised story — that stacking is what produced the 5/5.

An actionable theme or an explicit earnings headline cancels the penalty, so real events stay
intact. When adding a gate like this, always verify BOTH directions on live rows: the offending
item drops (STLD 5/5 → 1/5) **and** a genuine event keeps penalty 0 (TSMC record profit). A
filter only validated on the thing it was built to suppress will quietly eat real signal.

Surface every score adjustment in the UI as plain language (`scoreNotes()` in `JS_COMMON`
renders `inputs.material` / `inputs.adjustments` / `inputs.reaction` as chips). An unexplained
number cannot be audited by the owner.

## Re-running stage 3 over already-decided news

Stage 3 only picks up items with no stage-3 decision, capped at `max_calls_per_cycle` (5). To
rescore after a scoring change: back up the DB, `DELETE FROM signals` plus
`DELETE FROM screening_decisions WHERE stage = 3`, then run several cycles — one cycle handles
only 5 items, so a backlog needs repeated runs. Deleting stage-1/2 decisions instead would
force needless LLM spend and lose the original screening audit trail.

Note that the same headline can exist as several rows from different domains: one copy may be
`not_significant` while another passes via the repetition trigger. Searching by title can
therefore show a "rejected" row while a sibling row is mid-pipeline.

## Alert formatting

Alerts carry no disclaimer — a single-user radar does not need "not financial advice" on every
message, and it buries the information in the notification preview.

Labels stay plain, values are wrapped in `<b>` (`_field()` in `signal_delivery.py`), so the
ticker, chain, direction and score are what the eye lands on. Consequences to respect when
touching this:

- Outbox payloads are now Telegram HTML, so `deliver_pending()` must pass `parse_mode="HTML"`.
- The console channel must strip the markup (`_plain()` in `delivery.py`) or it prints raw tags.
- Escape label and value SEPARATELY; a `<` or `&` in a GDELT headline otherwise smuggles markup
  into the message and Telegram rejects the whole send with HTTP 400.

Always verify a formatting change against the real Telegram API (`_send_telegram` with a live
signal row), not only in tests: a malformed entity is a send-time 400, invisible to unit tests
that assert on the payload string.

## Price history

Backfill through the existing collector rather than new fetch code — it already has the
yfinance primary / Stooq fallback and upsert logic:

```
<uv> run python -c "...collect_prices(client, storage, graph, now_ms=..., days=1830)"
```

- Back up the DB to the scratch dir and stop the collector service before a bulk load, so a
  partial write cannot corrupt a live cycle.
- Stooq returns 404 for plain US tickers that yfinance serves fine; a `fallback: 0` stat is
  success, not a silent degradation.
- 28 symbols × 5 years ≈ 35k bars ≈ 5 MB of SQLite — bulk history is cheap here, so prefer
  fetching a long window once over many incremental calls.

## Admin UI conventions

Flat, operational, dark neutral-gray base with at most two restrained accents. Forbidden:
gradients, glassmorphism/blur, translucency, glow, icon-toppers, centered hero layouts,
rainbow palettes, decorative emoji, marketing/bento styling. Motion is functional only
(stagger reveal, drawer open/close, chart draw-in) and must respect
`prefers-reduced-motion`.

- Vanilla inline HTML/CSS/JS only. No React/Vue, no build step, no new JS dependency — draw
  charts and graphs as hand-built SVG.
- The user reads this on a phone: tables need local horizontal scroll with a sticky first
  column, and canvases need pinch-zoom plus `+ / − / Fit` buttons.
- Present stored metadata as meaning, not raw fields: map tone to a labelled scale, translate
  theme codes to readable phrases, parse quotations out of their `offset|length||text` wrapper,
  resolve node IDs to names, and state in words why an item passed or was filtered.
- Zoom on a time series belongs on the **time axis** with the price axis auto-rescaling to the
  visible slice; geometric viewBox scaling makes a multi-year series unreadable. Report the
  summary stats for the visible window, not the whole set.
