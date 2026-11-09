---
name: crypto-market-analysis
description: "Use when analyzing crypto markets and BTC–altcoin links."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [crypto, bitcoin, altcoins, market-analysis, investing, research]
    related_skills: [grounded-citations, be-ambitious]
---

# Crypto market analysis and investor education

## When to Use

Use for medium/long-term crypto investment education, BTC–altcoin dependence, changing market regimes, indicator interpretation, and evidence-based audits of commentators or strategies.

## Procedure

1. **Define the decision and horizon.** Ask only for missing high-impact details: holding period, base currency, acceptable drawdown, liquidity needs, jurisdiction if taxes/exchanges matter, and whether the user wants education or a portfolio decision. Distinguish spot investment from leveraged trading; never convert a descriptive indicator into a buy/sell instruction.
2. **Start top-down, then teach with one concrete asset pair.** Assess macro/risk regime (rates, dollar, equities, liquidity); BTC regime and its changing link to risk assets; intra-crypto rotation (BTC dominance, ETH/BTC, ALT/BTC); leverage/crowding (funding, open interest); and asset-specific economics (usage, fees versus tokenholder accrual, supply/unlocks, security, governance). Explain what each measure means, where to inspect it, what could fool it, and which decision it could change. Prefer a compact weekly reading routine to an indicator dump.
3. **Measure dependence rather than assert it.** Align timestamps, quote currencies and trading calendars; compute return correlations over multiple rolling windows, OLS beta of alt returns to BTC, and the residual/relative return. Recompute in rising, falling and stress regimes, since pooled correlation hides regime changes. An ALT/USD gain can still be an ALT/BTC loss; beta is an estimate over a past window, not a promised multiplier tomorrow. For small/illiquid coins, account for stale prices, exchange fragmentation, spread and survivorship.
4. **Separate description, prediction and implementation.** A crowded funding rate describes positioning, not an automatic reversal; on-chain activity is not tokenholder cash flow; a chart level is an invalidation condition, not proof. Compare any prospective signal to BTC buy-and-hold and a simple price-only baseline on out-of-time periods. Include fees, spread, slippage, funding, liquidity and maximum drawdown before discussing investability. State when an effect is untested or tested only on reused data.
5. **Investigate a commentator using primary evidence.** For a time-bounded Telegram-channel audit, paginate `https://t.me/s/<channel>?before=<oldest_id>` until the posts cross the start date; parse each message's ID, timestamp, text, linked URLs and attached-photo background image URLs, deduplicate by ID, and count the covered posts. Inspect relevant image pixels and linked chart/article content rather than treating captions or thumbnail previews as the full source. Track dated disclosures in a ledger: asset, direction, size if disclosed, entry, later partial exits, stop/invalidation, and latest explicit status. Distinguish the author's claim, contemporaneous information, and outcome; never call a stale position current merely because no exit was found. Seek auditable trades, sizing, fees, benchmark, Sharpe calculation, drawdown definition, walk-forward/live track record and losing periods. Treat published performance numbers as *claims*, not independently verified results. When a post's text and its attached performance image state different metrics, benchmarks, or periods, report the discrepancy and refuse to merge them into one track record — they are likely different strategies or different slices, and silently picking one manufactures a result the author never claimed. Check whether an attached chart is the author's own output or a cropped exhibit from someone else's report (numbered "Exhibit N", a trimmed source line, institutional styling) before attributing its analysis to them. Count distinct message IDs, not apparent volume: channels repost and re-pin the same text many times, so raw post counts overstate how much original material exists. If a shared notebook redirects to login, try authorized access or ask for an export; do not infer its contents from a public channel's excerpts. Telegram previews or linked material may be truncated or restricted: label the specific evidence gap, not an entire public channel as unreadable.
6. **Use external judges.** Cite primary data definitions and independent research for macro claims; if making quantitative claims, run reproducible calculations on raw historical data. Make a falsifiable thesis with an explicit horizon and failure condition. Present the educational framework first, then a short checklist the user can follow without you; avoid confidence theater or promises of profit.

## Standing presentation rules

Reply in Ukrainian for this user, with plain definitions and concrete BTC/alt examples. Distinguish relative performance in BTC from dollar profit; do not imply BTC and equities always correlate or that all altcoins share one beta. Keep near-term market opinions time-stamped and sourced. Do not pretend a source was read when only a snippet, redirect or restricted preview was available.

When the user says a source is hard to follow, answer the signal-to-noise question directly instead of defending the source: name which post types carry checkable content (a disclosed position, a named invalidation level, a changed macro view, a closed trade) and which are noise to skip, give a realistic read cadence, and say plainly whether it works as a hypothesis feed rather than teaching material. A diary-style author mixes a multi-year thesis, a multi-day trade, and automated-system output in one stream; spell out that these are different horizons, since reading them as one signal is what makes the channel feel contradictory.
