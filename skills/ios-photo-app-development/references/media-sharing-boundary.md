# Letting media cross a metadata-only boundary

A matcher that moves metadata only is easy to keep honest. The hard case is the
feature that genuinely needs the images: a result whose claim is "you were 40
metres apart" is not a result without the two photos that prove it. Implement
that as a **whitelist, never a permission**.

## The distinction

- A *permission* is a scope: an album, a city, a date range, a library. Once
  granted, what it covers is decided later, by whatever code runs next.
- A *release* is a finite, enumerated set of identifiers, derived from results
  that were already computed from metadata, with a recorded reason per item.

Only the second can be reviewed, shown to the owner, and revoked meaningfully.

## Type shape

- A `struct` with a private init, constructible only via
  `from(results:side:consents:)` and `from(results:side:session:)`. The caller
  must not be able to name an arbitrary asset and call it supporting material.
- Expose `allowsUpload(of:)` and make every uploader call it per asset. The
  guarantee has to live on the path to the network, not in a comment.
- Carry a `justification` list (which result, which place, which window released
  which ids) so an "why is this shared?" screen is derivable and the release is
  auditable.
- A static `.nothing(for:)` is the only value obtainable without consent.

## Rules the tests must pin

- **Mutual or nothing.** A one-sided yes releases nothing, *including that
  person's own media*. Assert both directions; releasing your own on a one-sided
  yes is the easy bug and it quietly makes the exchange non-reciprocal.
- **Narrowest source set.** Derive the release from the ranked results only.
  Never from a broader derived artifact — a map/overview layer that plots every
  item in the window summarises movement deliberately, and releasing media for
  each of its points hands over the whole window instead of the matches.
- **Own side only.** Each side releases its own identifiers; assert the two sets
  are disjoint and prefix-checkable.
- **Re-encode, never forward the original.** Originals carry EXIF GPS, device
  serial, and timestamps. Ship a bounded preview (longest edge, e.g. 1600 px),
  record the size in the payload so a reviewer can confirm it, and refuse
  oversized or empty data.
- **Bounded batch.** Cap items per side so result-count growth cannot turn the
  exchange into a bulk transfer.
- **Revocation is terminal.** A revoked pair releases nothing regardless of prior
  agreement; test it after a full successful release.
- **Payload identity.** Reuse the opaque per-pair id already used for the item's
  metadata so the recipient can attach the image to the result it proves, and
  assert the payload has no local identifier, coordinate, or capture timestamp.

## Why to write the narrowing tests first

The test that says "the overview layer must not drag its media along" is the one
that exposes whether the underlying results were ever narrow. Writing it before
the uploader surfaces an over-broad matcher while it is still only a ranking bug,
rather than after it has become a disclosure.
