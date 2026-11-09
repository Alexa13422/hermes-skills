# Stockholm (SL) + Arlanda airport

All endpoints below are keyless and were verified working.

## Stop/site lookup

```
curl -s 'https://transport.integration.sl.se/v1/sites?expand=true' -o /tmp/sites.json
```

Dump once, then grep locally. Useful IDs:

- `1080` Stockholm City (pendeltåg hub)
- `9000` Stockholms central
- `1079` Stockholm Odenplan
- `9500` Märsta (station + bus plaza)
- `9511` Arlanda central (pendeltåg platform)
- `5006` Sky City / Terminal 4 och 5
- `5002` Arlanda terminal 2 och 3

The journey planner wants **global IDs**, not these site IDs: prefix pattern `9091001000000000 + site_id` (so site `1080` → `9091001000001080`, `5006` → `9091001000005006`).

## Departures board

```
curl -s 'https://transport.integration.sl.se/v1/sites/<site_id>/departures?forecast=1200&transport=TRAIN'
```

- `transport` is one of `TRAIN`, `BUS`, `METRO`, `TRAM`, `SHIP`; optional `&line=41`.
- `forecast` is minutes and is capped at **1200** — larger values return HTTP 400.
- `date`/`time` params are accepted but **ignored**; the board is always "from now". Use the journey planner for a future time.
- Each departure carries `stop_point.designation`, which is the platform/`läge` letter to tell the user.

## Journey planner (v2)

```
curl -s 'https://journeyplanner.integration.sl.se/v2/trips\
?type_origin=any&name_origin=<global_id>\
&type_destination=any&name_destination=<global_id>\
&calc_number_of_trips=3\
&dep_arr_macro=arr\
&itd_date=20261007&itd_time=2100'
```

Parameter quirks, all learned by trial:

- `type_origin` / `type_destination` are **required** alongside `name_origin` / `name_destination`. Using `origin_id` / `destination_id` returns 400.
- `calc_number_of_trips` is required and capped at **3**.
- Date/time **must** be `itd_date=YYYYMMDD` + `itd_time=HHMM`. The obvious spellings (`date=`, `time=`, `datetime=`, `when=`, `itdDate=`, `itdTime=`) are accepted without error but silently return trips starting *now*. Always verify the first leg's `departureTimePlanned` matches the date you asked for.
- `dep_arr_macro=arr` plans backwards from an arrival deadline; `dep` plans forwards.
- Response root is `{"systemMessages": [...], "journeys": [...]}`; each journey has `tripDuration` (seconds), `interchanges`, and `legs[]` with `origin.departureTimePlanned`, `destination.arrivalTimePlanned`, and `transportation.number` (absent on walking legs).
- Timestamps are **UTC with a `Z`** — add the local offset (CEST = +2) before showing them.
- Write the response to a file with `-o` and parse the file; inlining the body through a shell pipeline can truncate it mid-JSON.

### Endpoints that do NOT help

- `journeyplanner.integration.sl.se/v1/trips` returns 502 — use v2.
- ResRobot (`api.resrobot.se/v2.1/...`) needs a Trafiklab `accessId`; without a key every call is 401.

## Arlanda fare geometry (the real reason this matters)

Two ways from central Stockholm to the airport on an ordinary SL ticket:

- **Pendeltåg 40 direct to Arlanda central** — ~38 min, but Arlanda station charges a **passage supplement (~150 SEK)** on top of the SL ticket.
- **Pendeltåg 41 to Märsta (terminus), then bus 583 → Sky City / Terminal 4+5** — ~55–65 min, **no supplement**: a single SL ticket (~43 SEK) covers it. Buses enter airport grounds by road, bypassing the station gate.

Operational details:

- Line 41 to Märsta runs every 15 min off-peak (:00/:15/:30/:45 from Stockholm City); the Stockholm City → Märsta leg is ~37 min.
- At Märsta the bus plaza is a 2–3 min walk from the platform; Arlanda buses leave from **läge A**.
- Bus **583** is the fast one (~11 min to Sky City). Bus **579** also shows "Arlanda" but routes via Sigtuna and takes ~17 min — it often covers evening slots, so read the board rather than assuming 583.
- Sky City → Terminal 5 is a further ~5 min walk indoors; budget it.
- Arlanda Express is ~18 min and ~340 SEK — mention as the speed option only.

Always warn the user **not** to board line 40 by mistake; it is faster and lands them with the supplement.
