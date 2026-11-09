---
name: race-card-handicapping
description: "Race cards to ranked picks: form, weights, riders."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [horse-racing, prediction, pdf, sports, analysis]
    related_skills: [grounded-citations]
---

# Race card handicapping

Turning an official race-day program (usually a PDF) into a ranked prediction with stated reasoning for a named race.

## When to Use

- The user drops a race-program PDF/URL and asks who wins, or asks for analysis of a given race time.
- The user wants a field broken down (form, weights, jockey/trainer, breeding) before betting.
- Do NOT use for general "is betting worth it" questions with no specific card.

## Step 0 — Check whether the race has already run

Before any analysis, compare today's real date (query it: `date`) against the card's race date and post time. Context headers can be days stale, and a program PDF covers a weekend that may already be over. If the race is past, pull the **result** and deliver a post-race breakdown instead of a prediction — a confident forecast of a finished race destroys trust in everything else in the answer. Say explicitly which it is.

## Procedure

1. **Date check** (above). Decide prediction vs post-mortem.
2. **Confirm which race.** A card has many races and several share the same minute across days. Restate distance, race number, date, and conditions before analysing so a mismatch surfaces immediately.
3. **Extract the card properly.** Download the PDF and run `pdftotext -layout file.pdf file.txt`, then grep for horse names to locate the race block. Generic web extraction flattens the multi-column program layout and silently drops the per-horse form strings and result tables — the single most valuable column on the page.
4. **State your data gaps up front.** If individual form lines did not survive extraction, say so and name what you ARE using (weights, jockey/trainer season stats, breeding, official tips). Never dress structural inference up as form analysis.
5. **Pull season statistics** from the program's own rankings pages — jockey and trainer win counts and strike rates. These are the highest-signal numbers that survive any extraction.
6. **Read the stewards' rulings section.** Suspensions, disqualifications, and penalised stables change who can actually ride and which runners are risky. Rulings are printed at the back of the program and are invisible in any race-block summary.
7. **Verify the final field against a live results/start-list source** (see references). The printed program is typeset days ahead; riders get swapped and horses get scratched. A pick built on a jockey who was replaced is a wrong pick for the right reason.
8. **Rank with explicit reasoning per runner**, then give a top pick, a danger, and a value pick.

## Handicapping signals, in order of weight

1. **Who is actually in the saddle on the final start list** — in a tight finish the rider's strike rate decides it, and the program's printed rider is frequently not the one who rides.
2. **Stable's own revealed preference** — when one trainer runs two horses, the one carrying the stronger-ranked jockey is the stable's bet. Read the weaker rider (apprentice, `k.dż.`, `st.u.`, `pr.dż.`) as a demotion signal, not a neutral fact.
3. **For 2-year-olds, foaling date** — a January–March foal against a late-April/May one is 2–3 months more development; on short sprints that beats rider class outright.
4. **Weight in handicaps** — top weight means the handicapper rates the horse highest, so it is a class signal and a burden at once; say which way you are reading it.
5. **Breeding matched to the distance** — sire lines for precocious sprinters vs stayers that need next season and 1600 m+.
6. Trainer and breeder/stud quality — real but weaker than the above.

## Output format (this user's preference)

- Open with the data caveat in one line if there is one, then the race header (distance, class, purse, field size, going).
- One block per runner: number, weight, rider, trainer, breeding, then the verdict sentence that actually decides placement.
- Then the ranked prediction with a one-paragraph rationale for the top pick naming the decisive signal.
- Close with a short **nuances** block (suspensions, stables under scrutiny, scratchings) and an offer to go deeper with real form data.
- Post-mortem variant: lead with the factual finish order, times and margins, then a section on which signals actually worked and where your own reasoning was wrong. Own the miss concretely — that is the part with information in it.
- No tables. Minimal narration of how you queried anything. Reply in the user's language, keeping horse, rider, and track names in original spelling.

## Pitfalls

- **Sectional times tell you the shape of the race.** Even splits mean nobody got away and the finish was decided in the straight (expect head/neck margins); a fast first split and slow last means the leaders emptied out. Use this to explain small margins rather than claiming superiority.
- **A huge beaten margin plus a top rider is a readiness signal, not a rider failure.** Check age and foaling date before blaming the ride.
- **Scratchings invalidate official tips silently.** If one of the program's own picks is a non-runner, note it rather than scoring the tips as wrong.

## References

- `references/sluzewiec-warsaw.md` — Tor Służewiec (Warsaw): program URL pattern, Polish program vocabulary, live results source and its consent gate.
