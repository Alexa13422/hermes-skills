# Persisting a pair across launches

A pair that only exists in memory is gone when the app is closed, and the two
people are asked to agree again. Persist it — but persist *acts*, not state.

## Store what each side did, replay it through the state machine

The stored snapshot records only the acts each side performed: joined,
consented (with the consent's own fields), revoked. Restoring re-executes those
acts against the live state machine rather than decoding a finished state.

Direct `Codable` conformance on the session object is the trap: anyone who can
write the app container hands you a session already in its most permissive
phase, carrying consents nobody gave. Replay means every guard that protects
the live flow also protects the file, for free and with no second code path.

Test what a forged file must NOT achieve: a consent attributed to a participant
who never joined, a duplicate consent, a refusing consent presented as
agreement, the same person on both sides, an out-of-order replay, a corrupt
range, and a snapshot from a newer schema version.

## Do not persist scan results

They are the largest and most sensitive part, cheap to recompute from the
library, and storing them means a revocation on the other device leaves that
person's signals sitting in your storage. A restored pair returns to
"ready to scan", never to a mid-scan or revealed phase.

## A revoked pair stays listed, but refuses to open

Deleting it makes a withdrawal indistinguishable from never having paired, so
the next launch cheerfully offers to pair again. Keep the record, mark it dead,
and have `open` throw rather than return a session whose every method throws —
handing back a live-looking object is an invitation to forget the phase check
at one call site.

## Store shape

- Make the store a protocol with an in-memory implementation for tests. The pure
  suite then runs on Linux where no platform container exists.
- One file per pair, not one combined file: a single unreadable record must not
  take the whole lobby down. Surface the per-record decode failure on that entry.
- Expose the per-entry failure to the UI as text, and keep "needs consent",
  "ready", "ended", and "unusable" distinguishable — they lead to different
  screens.

## Linux Foundation quirk

`FileManager.replaceItemAt` reports "the file doesn't exist" on Linux for the
overwrite case the call exists to serve, and it consumes the temporary file.
Write to a sibling, remove the destination if present, then `moveItem`. The
window this opens is harmless when a missing file reads as "not stored yet"
rather than as a pair with no consent.

## Device identity

Give the install its own random participant ID, persisted locally. Do not reuse
a platform-provided vendor identifier: a reinstall should read as a new person
rather than silently inheriting a previous pair's consent.

If the transport never sends the host's identity, the guest cannot know it and
will save a placeholder — the two devices then disagree about which side is
which. Exchange identity in the first frame of the handshake, or mark the gap
explicitly in the code and in the status report; it is not cosmetic.
