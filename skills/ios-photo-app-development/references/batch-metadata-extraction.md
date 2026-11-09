# Reading a library's metadata fast, for a date range

The scan happens while two people wait on it, over a library of tens of
thousands of assets. Speed is a design constraint, not an optimisation pass, and
the expensive mistakes are invisible to a correctness test: they produce
identical results and take minutes-to-hours instead of seconds.

## Rules, strongest first

- **Never resolve assets one at a time.** The per-asset info call is one IPC
  round trip per photo and, for cloud-backed assets, may pull the original down
  over the network — a data bill as well as a wait. Take whatever the batch query
  returns and design matching around that.
  - On iOS via `expo-media-library`, `getAssetsAsync` does **not** populate
    `location` in a batch; coordinates are documented as available only through
    `getAssetInfoAsync` per asset. Treat that documented path as unusable at
    library scale and decide deliberately what the product does with the batch
    fields it does get, rather than silently looping.
- **Let the platform filter the window.** `createdAfter`/`createdBefore` is an
  indexed query. Fetching everything and filtering in JS walks the entire
  library to find a window that may hold 2% of it.
- **Page, and yield as pages arrive** (async generator over the cursor).
  Clustering then starts on page one, progress is real rather than a spinner, and
  a cancelled scan stops after the current page instead of after the library.
- **Sort oldest-first** when the core segments by time: handing a newest-first
  stream to day/stay segmentation splits stays at the wrong boundaries.
- **Get the total from one page of size 1** — the batch response carries the
  query's total count, so a determinate progress bar costs one call rather than a
  full enumeration. Treat a missing count as "indeterminate bar", never as a
  scan failure.
- **Touch no pixels.** Nothing in the adapter may read a URI, request a
  thumbnail, or download an original. Where the product has an enumerated media
  release, the adapter must not become a second path around it.

## Timezone must come from the photo's place

The platform exposes no per-asset timezone, and both easy answers are wrong:

- Returning `null` makes a core that requires a zone drop **every** asset — the
  scan yields nothing, silently, and looks like an empty library.
- Using the device's *current* zone places a photo taken abroad on the wrong
  calendar day, which directly changes whether two people "shared a day".

Resolve the zone from the asset's own coordinates with an **offline** lookup
(`tz-lookup` is ~150 KB and covers the globe; declare a `.d.ts` for it as it
ships no types). Drop a photo whose place is unknown rather than guessing — it
was never going to match on place anyway. After wiring any adapter, check what
the core requires per signal and assert a non-empty result on a fixture, or a
missing field turns the whole feature into a no-op.

## Offline city resolution

A network geocoder means thousands of requests per scan and sends the user's
location history to a third party to power a feature whose premise is that
nothing leaves the phone. Resolve a **coarse grid cell** instead of a city name:

- Cell ~0.25° of latitude (~28 km) keeps one metropolitan area together while
  separating genuinely different towns.
- Scale longitude by `cos(latitude)` (clamped away from zero) so cells stay
  roughly square instead of collapsing into slivers at high latitude.
- Put the resolved IANA zone **in** the identifier: one cell can straddle a zone
  border, and merging those places lands photos on the wrong calendar day.
- Cache per cell, not per photo.
- A grid cell is also more honest than a guess: a geocoder labelling a
  coordinate "Warsaw" when it is 40 km outside produces a chapter titled with a
  city neither person visited. Derive any display name from the zone's last
  component, which is at least a real administrative label.

## Tests that are worth their keep here

Assert the cost, not the arithmetic — these are the properties a correctness
test cannot see:

- Across ~1000+ fake assets, the per-asset info call count is **exactly zero**,
  and the page-call count is greater than 1 but bounded.
- An asset outside the requested window is never enumerated (proves the platform
  query filtered it, not a JS pass).
- Progress callbacks fire more than once and increase.
- An abort mid-scan leaves far fewer assets enumerated than the library holds.
- A screenshot and a coordinate-less photo both yield no signal.

Build the fake platform module with counters (`pageCalls`, `assetInfoCalls`,
`enumeratedIDs`) and have it do the date filtering itself, so the
"window was filtered by the query" assertion means something.

## Mocking the platform module in an ESM test runner

Mock the module rather than injecting a seam into the adapter: an adapter read
through a test-supplied seam proves nothing about the call it really makes.
Under Vitest/ESM the sequence is `vi.doMock(...)` → `vi.resetModules()` →
`await import('../Adapter')`. `require` is not available and fails with "Cannot
find module"; the helper that does this must therefore be `async`, and
`resetModules` is what stops a later test reusing an earlier mock.
