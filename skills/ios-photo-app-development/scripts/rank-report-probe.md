# Deterministic probes for "how does it work right now?"

When the user asks what the current thresholds, ordering, or hierarchy are,
reciting constants from a source file or from memory is how a confidently wrong
answer gets shipped. Interacting constants (weights times decay curves, band
lookups, tie-breaks) do not produce the ordering you would predict by reading
them. Print the real numbers from the real code.

## The loop

1. Write a throwaway probe as a temporary test in the project's own suite, so it
   links against the shipped types rather than a reimplementation. A standalone
   script that re-derives the formula proves nothing about the code that runs.
2. Have it `print` three things: each axis's curve at representative inputs, a
   worked ordering of concrete realistic cases sorted by the real scorer, and the
   same cases under every shipped variant.
3. Run with the suite's own filter (`swift test --filter ProbeTests`) and grep for
   the marker you printed.
4. Add break-even questions the user will ask next ("how far can it be and still
   outrank X?") as a bisection inside the probe, not as arithmetic in your head.
5. **Delete the probe before committing**, and re-run the full suite after
   deleting. A probe left in the tree reads as a real test, asserts nothing, and
   the next session will maintain it.

## Why a probe, not a formula

Two findings this loop produced that reading the source did not:

- A floor/ceiling overlap — the worst possible same-day result outscored the best
  possible next-day one, because the day axis contributed its full weight for
  free. Visible only by evaluating both extremes.
- A boundary case where "same moment" was decided by calendar day, so a
  twenty-minute gap across midnight scored less than half the identical gap at
  midday. The constants looked right; the ordering did not.

## Reporting the result

Give the curves as small tables, then the worked ordering, then the two or three
consequences worth seeing (near-ties, floors and ceilings that overlap, where an
axis stops mattering). Flag thresholds you chose yourself as uncalibrated when no
real data has been run through them — a confident table invites the user to treat
guessed constants as measured ones.
