---
name: transit-trip-planning
description: "Plan transit routes with exact times from operator APIs."
version: 1.0.0
author: hermes-curator
license: MIT
metadata:
  hermes:
    tags: [transit, travel, timetable, airport, api]
    related_skills: [product-price-monitor]
---

# Transit trip planning

Planning a door-to-door public-transport route (airport runs, intercity connections, "which train at what time") where the user needs **exact vehicle numbers and clock times**, not prose advice.

## When to Use

- The user asks which train/bus/metro to take, at what time, to reach a place by a deadline.
- The user asks how to get to or from an airport, or whether a cheaper routing exists.
- The user shares a travel-hack screenshot or video and wants it turned into a real itinerary.
- Do NOT use for generic "is this city walkable" or fare-policy-only questions with no departure times involved.

## Core rule

Never answer a "which train / when do I leave" question from blog posts, Rome2Rio summaries, or memory. Those give averages and stale intervals. Query the operator's own timetable API and report the specific departures it returns. Web search is only for *fare rules and gotchas* (surcharges, zone boundaries, ticket validity windows) — never for departure times.

## Procedure

1. **Pin down the hard constraint.** Arrival deadline or desired departure time, date, and the exact destination node (terminal number, not just "the airport"). If the user gives an arrival target, plan with an arrival query, not a departure query.
2. **Resolve stop IDs first.** Fetch the operator's stop/site list once, dump it to a file, and grep it locally for candidate names. Never hand-guess numeric IDs. Airport terminals are often one combined stop (e.g. "Sky City/Terminal 4 och 5"), and the rail station at an airport is a *different* stop from the bus stops.
3. **Run the trip query** for the target date/time; ask for 3 alternatives so you can show one earlier and one later option.
4. **Cross-check with a departures board** for the first leg's stop. If the planner and the board disagree on headway, trust the board for frequency and the planner for the connection.
5. **Check the fare trap** with a web search for the corridor (surcharges, airport passage fees, separate-operator legs). A route that is 20 min slower but avoids a 150-unit surcharge is usually what the user actually wants — state both and recommend one.
6. **Build in slack.** Recommend the option with ~15 min buffer before the deadline as the primary, then list the tighter and the earlier alternative. Say explicitly what happens if they miss it (next headway).

## Output format (this user's preference)

- Lead with ONE recommended itinerary as a vertical time-stamped chain: `HH:MM — line/number, from stop, direction` → one line per leg → arrival.
- Then 1–2 alternatives under short labels ("tighter", "earlier").
- Then a short **Important** block: headway if they miss it, the line to *avoid* and why, ticket type and price, platform/stop designation (`läge A`), walking time inside the station.
- No tables. No narration of how you queried the API. Findings only.
- Reply in the user's language (Ukrainian by default here) while keeping station, line, and platform names in the local spelling — they must match what's printed on the signs.

## Pitfalls

- **Weekday vs weekend schedules differ.** If the user gave a vague date, plan on a weekday and close by asking for the exact date, offering to re-check.
- **Timetable APIs usually return UTC.** Convert to the local timezone before showing times, or you will send the user to the station two hours early.
- **Confirm the planner honoured your requested date/time** by reading the first leg's timestamp in the response. Several parameter spellings are silently ignored and fall back to "now", which produces a plausible-looking but useless itinerary.
- **Cheap-route hacks hinge on the transfer being physically short.** State the walking time and platform, because the whole saving collapses if they miss the connecting bus.
- **Ticket validity windows** (e.g. 75 min single) can expire mid-journey on the slower route — check the itinerary's total duration against the window and warn if it is close.

## References

- `references/sl-stockholm.md` — Stockholm / SL + Arlanda: working endpoints, stop IDs, parameter quirks, the Märsta surcharge bypass.
