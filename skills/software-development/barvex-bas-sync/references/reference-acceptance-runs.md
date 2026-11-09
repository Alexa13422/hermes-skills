# Acceptance runs for BAS reference links (brand, category)

Depth for proving brand/category link behaviour against a real Medusa DB. The
always-on rules live in SKILL.md; this file holds the sequence, the SQL shapes
and the remote-execution mechanics.

## Table names

- Product↔brand link: `product_product_brand_brand` (the module prefix is
  doubled; `product_brand_brand` does not exist).
- Product↔category: `product_category_product`.
- Both carry `deleted_at`; a dismissed link is a soft-deleted row, so always
  filter `deleted_at IS NULL` when counting active links.

## Clone discipline

Clone from the pristine source DB with a parameterised script. Hardcoded
source/target names make the script unusable for the second run and tempt a
rerun against an already-dirty clone. Guard inside the script:

- assert the target does not already exist (refuse to overwrite),
- assert `.env`'s current DB name starts with the test prefix, so the script can
  never point production at itself,
- rewrite only the DB path segment of `DATABASE_URL`, and print names only —
  never the connection string.

After a write-path fix, clone again from the pristine source. A previously
failed clone holds half-written products that mask whether the fix works.

## Seed references before the first sync

Seed the brand's BAS id and each category's `metadata.bas_external_id` BEFORE
syncing, or every product carrying a reference fails NOT_FOUND. Make the seed
script idempotent (look up by BAS id, then by handle, only then create) — a
duplicate BAS id is exactly what the resolver is supposed to reject, so an
accidental double-seed poisons later passes.

## The sequence that actually proves the fixes

1. **References missing.** Sync with nothing seeded. Expect the run to fail
   (`<resource>|failed|N|M`), the watermark unchanged, and manual links
   untouched. This proves resolve-before-write: no half-created product, no
   stripped association.
2. **Seeded, synced twice.** Expect `idle` with zero failures and byte-identical
   link counts across both passes. Equal counts on the second pass is the only
   evidence of idempotency.
3. **Manual category added on a BAS product, then sync.** The manual category
   must survive alongside the BAS one. This is the regression for `category_ids`
   replacing the whole set.
4. **Move the BAS id to a different brand, then sync.** Must not raise
   `Cannot create multiple links`, every affected product must end on the new
   brand, and the link table must show exactly one dismissed row per product —
   not growth across repeated passes.
5. **Strip the reference field from the fixture entirely, then sync 2–3 times.**
   Both manually linked and previously BAS-linked products keep their links.
   This is the proof that absent means "not managed", not "unlink".

## Reading the counts without fooling yourself

A clone of production carries unrelated links, and fix-up scripts you ran
yourself add dismissed rows. Never read a bare total. Group by the BAS key:

```sql
SELECT coalesce(p.metadata->>'bas_external_id','NON_BAS') AS k, count(*)
FROM product_product_brand_brand l
JOIN product p ON p.id = l.product_id
WHERE l.deleted_at IS NOT NULL
GROUP BY k ORDER BY k;
```

PostgreSQL rejects an aggregate inside the GROUP BY expression, so alias the key
and group by the alias rather than repeating a concatenation that contains
`count(*)`.

To prove ownership of each link, join the brand row and print its BAS id:
`NULL` there means an admin-created brand, which is what must survive a sync.

## Remote execution mechanics

Inline SQL inside `ssh host 'wsl ... psql -Atc "..."'` is mangled: quotes
collapse and `%` dies. The same string also eats `grep -iE 'a|b'` and `$?` —
cmd.exe reports `'error' is not recognized`. Put every SQL check, grep pipeline
and exit-code capture in a `.sh` file instead.

Transfer with `scp` to the Windows-style path (`host:C:/Users/<user>/file.sh`);
the `/mnt/c/...` form fails as an scp destination. Run it as
`wsl --exec bash /mnt/c/Users/<user>/file.sh <args>`, passing the DB name as an
argument so one script serves every clone.

Before blaming the sync for an unreachable host, check `tailscale status`: a
sleeping machine reports `offline, last seen Nm ago` while `tailscale ping` may
still succeed once it wakes.

## Exercising "the source stops sending a field"

To simulate the upstream dropping a field, strip it from the fixture server with
a regex over the fixture literals, keep a `.bak`, and restart the container.
State in the report that the fixture was modified and can be restored — a
modified mock left undocumented makes the next run's baseline inexplicable.
