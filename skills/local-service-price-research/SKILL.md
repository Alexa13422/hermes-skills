---
name: local-service-price-research
description: "Use when comparing current local service prices and terms."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [prices, local-services, comparisons, healthcare]
    related_skills: [grounded-citations, blocked-page-recovery]
---

# Local service price research

## When to Use

Use for a request to compare current prices of a service in a particular city, especially medical tests where two similarly named packages can deliver different results.

## Procedure

1. **Pin down the deliverable before searching.** Parse the service, city, recipient, and whether the user wants every named component performed or only a conditional workflow. Interpret a brief correction to the noun as clarification of the same request; don't restart the topic. For combined medical tests, distinguish a package that runs both tests for everyone from reflex testing that runs the second only after a positive first result.
2. **Search provider-owned offer pages across major chains and local clinics**, not just aggregators. Search in the local language using synonyms and test names. For an exhaustive-sounding request, state coverage accurately: a broad market scan is not literally every provider. Date the check.
3. **Extract the live product page and verify each quote**: exact tests and genotypes, city-specific price, online vs walk-in price, promotional code and expiry, collection fee, sample-collection method, eligible location, and whether the package is available there. A city listing with a price 'from' is a floor, not a confirmed checkout quote. Never promote a search snippet or a 30-day-low display into today's price. If a page is blocked, use the blocked-page recovery workflow for context but do not treat an archived price as current; label snippet-only prices unconfirmed.
4. **Separate offers by fulfillment:** in-person swab, mail-in kit, and conditional/reflex testing are not interchangeable. Check who may collect a clinical sample; do not infer self-collection from the existence of a home kit. Separate public-program eligibility and conditional test sequence from the private package comparison.
5. **Rank like-for-like, confirmed options first** with direct source links and concise caveats on location/promotion; list noncomparable or unconfirmed prices separately. If the user's age or clinical indication affects eligibility, state the condition rather than assuming it. For medical decisions, cite primary provider and public-health sources and avoid prescribing a screening interval without context.
6. **Verify the final citations and uncertainty.** Use `grounded-citations` for a source ledger and evidence checks; don't claim exhaustive coverage, guaranteed final checkout price, or successful booking without testing those facts. Give the cheapest verified option and a practical next check (select a specific collection site and confirm final price) rather than burying the recommendation under source dumps.
