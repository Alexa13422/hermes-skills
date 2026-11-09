# Historical GDELT backfill and full backtest

Read this before promising any predictive-accuracy claim, and before writing fetch code that
walks GDELT backwards in time.

## Why live collection can never produce a backtest sample

`collect_gdelt()` reads `lastupdate.txt`, which names only the **newest 15-minute GKG slice**.
So the news table only ever grows forward from the day the collector was first started, and
every stored item stays newer than the newest daily price bar for its first session or two.
Waiting does not fix the shape: you accumulate recent news at the same rate the price history
advances. A historical sample has to be fetched explicitly by timestamp.

## Establish the measurable sample before tuning or claiming anything

Run this first. If `measurable` is 0 across the board, no scoring claim is supported by data
and the honest answer is "unmeasurable yet", not a tuned threshold.

```sql
SELECT s.score, COUNT(*) total,
  SUM(CASE WHEN (SELECT COUNT(*) FROM price_bars p
                 WHERE p.symbol = s.ticker
                   AND p.date > date(s.news_published_at_ms/1000,'unixepoch')) > 0
           THEN 1 ELSE 0 END) measurable
FROM signals s GROUP BY s.score ORDER BY s.score;
```

For a 21-day horizon require `> 21` closed bars, not `> 0`. Report the measurable count per
horizon separately — a sample that supports a 1-day return usually cannot support 21.

## Fetching historical slices

Slices are addressable directly, no master list needed:

```
https://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip
```

Slices exist at `:00:00`, `:15:00`, `:30:00`, `:45:00` of every hour.

- Use **https**. The `http://` form returns 301 and `curl` without `-L` writes a 0-byte file
  that then fails as `BadZipFile` — a redirect masquerading as a corrupt archive.
- `masterfilelist.txt` is ~128 MB and lists every slice since 2015-02-18. Never download it to
  discover URLs you can already construct from a timestamp.
- Measured per slice: ~4.9 MB zip, ~1218 rows, ~1.3 s to download, ~0.24 s CPU to
  parse + match, ~74 rows matching the current graph (~6%).

### Project the cost from one measured file before launching a long run

One hourly slice per hour: 5 years = 43800 files ≈ 210 GB transferred ≈ 2.9 h CPU;
1 year = 8760 files ≈ 42 GB ≈ 0.6 h. Multiply a real measurement, never guess, and state the
numbers to the owner before starting — a run of this size is a decision, not a detail.

## Rules for the backfill job itself

- **Stream and discard.** Never persist the zips. Keeping 210 GB of archives buys nothing when
  only ~6% of rows match and the parse is 0.24 s.
- **No title fetches.** `resolve_title()` issues a live HTTP GET per row, which is why the live
  collector caps it at 30 per cycle. At backfill scale it is impossible — use `_slug_title(url)`
  only, and expect the slug-quality caveats from `references/news-filtering-design.md`.
- **Keep a resume ledger** keyed by slice timestamp, written as each slice completes. A
  tens-of-thousands-file job will be interrupted; without the ledger a restart redoes everything.
- **Per-file error isolation.** A 404, timeout, or bad zip increments a counter and the loop
  continues. One bad slice must never kill a multi-hour run.
- **Bound memory.** Parse, extract matched rows, drop the file's rows before the next iteration.
- **Write to separate tables** (`historical_news`, plus the slice ledger). The live
  `news_items` / `screening_decisions` / `signals` rows are the audit trail and must stay intact.
- Reuse `parse_gkg`, `_match_parts`, `_field`, `_tone`, `_timestamp_ms` and `Vocabulary` from
  `gdelt.py` rather than forking the parse — a second copy of the column offsets will drift.

## The backtest must be LLM-free

Five years of hourly slices yields millions of candidate rows. Stage 2/3 screening over that is
unaffordable and pointless. Score the historical sample with the deterministic path only
(`significance.py` + `analysis.compute_score`), which is also the methodologically correct
choice: it measures the *rules*, not a model's mood on the day it was asked. LLM screening stays
live-only. If a scoring path cannot run without an LLM call, report that as a blocker instead of
substituting a proxy score.

## Pilot, report, stop

Never let the first historical run be the full range. Run a bounded pilot (a few months,
~4400 slices), then report real numbers read out of the DB — slices attempted/succeeded/errored,
row count, date span, rows per ticker, how many rows clear each return horizon, wall clock and
volume transferred. The owner decides whether the pilot justifies the full run. Estimates
presented as results are the failure mode here.

## The outside judge

Forward return and abnormal return versus **SPY** at 1/5/21 days, computed on rows the scoring
never saw. `price_bars` already carries SPY alongside the 27 single names, so the benchmark needs
no new data source. Grade against that, never against a reread of the signal's own explanation.
