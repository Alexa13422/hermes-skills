# Hermes web-search backends

## Selection order

`tools/web_tools.py::_get_backend()` walks a fixed candidate tuple and returns the FIRST available. Re-grep it before relying on this list — the order is source of truth, this is a snapshot:

1. `TAVILY_API_KEY`
2. `PERPLEXITY_API_KEY`
3. `EXA_API_KEY`
4. `PARALLEL_API_KEY`
5. `KEENABLE_API_KEY`
6. `FIRECRAWL_API_KEY` / `FIRECRAWL_API_URL`
7. managed tool-gateway Firecrawl
8. `SEARXNG_URL`
9. `BRAVE_SEARCH_API_KEY`
10. `ddgs` package importable
11. keyless Firecrawl (last resort)

The code's own comment: explicit user credentials beat the managed-gateway probe; free tiers trail paid. A key added below an already-set one changes nothing — set the higher one or unset the incumbent.

## Symptom → cause

`Keyless Firecrawl search failed: 403 Forbidden` means no key is configured anywhere and the anonymous endpoint is rate-limiting. It is not a broken tool and not a network fault; it resolves by configuring any backend above.

`web_extract` and browser fallbacks use Firecrawl independently of which search backend wins, so a Firecrawl key remains useful alongside Tavily.

## Signup links

- Tavily — https://app.tavily.com/home — 1,000 credits/mo, no card, resets on the 1st. LLM-shaped snippets. First in the ladder, so it always wins.
- Brave Search — https://brave.com/search/api/ — 2,000/mo, card required for verification, independent index.
- Exa — https://dashboard.exa.ai/api-keys — starter credit, neural/semantic search.
- Firecrawl — https://www.firecrawl.dev/app/api-keys — one-off credits; also powers extract/crawl.
- Perplexity — https://www.perplexity.ai/settings/api — paid only.
- Parallel — https://platform.parallel.ai/ — AI-native search and extract.
- SearXNG — self-hosted, no key; set `SEARXNG_URL`.

## Recommended pairing

Tavily for search plus Firecrawl for extraction covers both paths without contention, since they occupy different roles rather than competing for the same ladder slot.
