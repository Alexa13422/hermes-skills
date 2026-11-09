# Tor Służewiec (Warsaw) — race cards and results

## Program PDF

- Published at `https://torsluzewiec.pl/wp-content/uploads/<YYYY>/<MM>/PG_<day>-<day>_<YYYY>.pdf`, one file per race *weekend* (e.g. `PG_37-38_2026.pdf` = race days 37 and 38, Saturday + Sunday). One file therefore contains two full cards; always confirm which day you are reading.
- Extract with `pdftotext -layout`. Font-weight syntax warnings are harmless. Grep horse names to find a race block; the blocks are ordered by post time.
- Neither `pdftotext -layout` nor web extraction preserves the per-horse **form strings** (`3–2–2–5–2`), star ratings, or career earnings — confirm with `grep -nE '[0-9][–-][0-9][–-][0-9]'` and expect no hits. When the user photographs the program page, `vision_analyze` on that image is the reliable way to recover form, stars, and zł totals; ask for a photo rather than inferring form.
- Useful back-matter, in order: results of the previous race weekend, stewards' rulings (`Orzeczenie Komisji Technicznej`), doping-test clearances, then season rankings for jockeys (`Ranking jeźdźców`) and trainers (`Ranking trenerów`) with wins / seconds / starts / strike rate.
- `NASZE TYPY:` at the end of each race block is the program's own four picks in order — a strong baseline worth stating and then agreeing or disagreeing with.

## Program vocabulary

- `dż.` jockey · `k.dż.` apprentice jockey · `pr.dż.` trainee jockey · `st.u.` senior work-rider · `u.` work-rider — descending competence, and a key read on stable intent.
- `P:` sire–dam · `H:` breeder · `W:` owner · `S:` stable · `T:` trainer.
- `okulary` = blinkers (on a 2-year-old, usually means it has already raced and lost focus). `(-2)` after a name is a weight allowance.
- `klacz` mare/filly · `ogier` colt/stallion · `wałach` gelding · `gniady` bay · `kasztanowaty` chestnut · `siwy` grey · `kary` black.
- Classes: `I grupa` best, `IV grupa` weakest; `czystej krwi arabskiej` = purebred Arabian (separate from thoroughbred `xx`).
- `gonitwa handikapowa` handicap · `WYC` withdrawn · `BY_VET` vet scratching · `styl: pewnie / łatwo / sent` winning manner · margins `łeb` head, `szyja` neck, `nos` nose, `daleko` far.

## Live results and final start lists

- `livejumping.com/ap/event/<event>/competition/<id>` carries Służewiec start lists and results, including rider substitutions the printed program does not have.
- The page sits behind a consent overlay that needs the **GO TO THE WEBSITE** button clicked **twice** (a second, longer notice replaces the first). Plain page extraction returns an empty body; drive it with the browser, then read `document.body.innerText`.
- Finding the right competition id: search the web for a runner's name plus `livejumping` — per-race ids are not derivable from the race number.
- Results give finish order, rider and weight, sire/dam, winning time with sectionals, margins, going (`FLEXIBLE 3,7`), temperature, and declared-vs-started counts.
