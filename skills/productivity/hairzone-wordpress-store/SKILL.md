---
name: hairzone-wordpress-store
description: "HairZone WooCommerce store via SSH + wp-cli."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [wordpress, woocommerce, wp-cli, seo, yoast, hostinger, ssh]
    related_skills: [blocked-page-recovery, service-and-credential-provisioning]
---

# HairZone WooCommerce store (Hostinger)

Use for hairzone.online: adding products, SEO metadata, categories, brands, or
diagnosing a site-wide 500. Store carries two brands: `Na Golov[y]` (hair care)
and `Na WKIR[y]` (body/hand care). Ukrainian-facing; Astra + `astra-child`
theme, Yoast SEO, LiteSpeed Cache.

## Access

```bash
ssh -p 65002 u588408061@82.25.96.26
cd domains/hairzone.online/public_html   # wp-cli works here, already installed
```

Key auth works (`~/.ssh/id_ed25519`). Never accept a password in chat.

## Command discipline (learn this first)

Every `wp` call over SSH is slow (seconds). Loops of 12 products × 8 metas will
blow past any timeout. Therefore:

- Generate a **single shell script** locally, `scp` it, run it once. Do not drive
  dozens of individual `ssh wp ...` calls.
- Run anything touching more than ~5 products with `background=true,
  notify=true`, or `timeout` ≥ 300. A killed mid-loop script leaves partial
  state — always re-verify afterwards, never assume.
- `set -euo pipefail` in the script, but redirect noise: `>/dev/null`. Thousands
  of "Success: Updated custom field" lines bury the real output.
- Do not pipe wp-cli output through `awk` with a `$1>=952` style filter inside a
  single-quoted SSH command — quoting collapses and awk prints its usage. Filter
  locally or use `grep`.

## Product taxonomy facts

- Products: post type `product`, drafts are legitimate (unpriced items).
- Attribute `Об'єм` is a **custom** (non-taxonomy) attribute, meta
  `_product_attributes`, key `%d0%be%d0%b1%d1%94%d0%bc`, name `Об&#039;єм`.
  Copy the exact JSON shape from an existing product rather than inventing it.
- Brand taxonomy is `product_brand` (NOT `pa_brand`, which exists but is empty).
- Category/tag names are Ukrainian; **slugs must be English**. WordPress
  percent-encodes Cyrillic slugs into unreadable URLs when a term is created by
  name, so always set `--slug` explicitly.

### Critical: pass term NAMES to `wp post term set`, never IDs

```bash
# WRONG — creates a junk term literally named "86"
wp post term set 952 product_brand 86
# RIGHT
wp post term set 952 product_brand "Na WKIR[y]"
```

Passing a numeric ID makes WooCommerce create a **new term with that number as
its name**. Always verify with
`wp post term list <id> <tax> --fields=term_id,name,slug`. If a junk term
appeared: `wp term delete product_brand <junk_id>`.

## Creating a product (verified template)

```bash
ID=$(wp post create --post_type=product --post_status=draft \
  --post_title="..." --post_excerpt="<1-2 sentences>" \
  --post_content="<~4 sentences>" --porcelain)
wp post term set "$ID" product_cat 'Креми для рук'
wp post term set "$ID" product_tag 'крем для рук' 'зволоження' 'новинка'
wp post term set "$ID" product_brand 'Na WKIR[y]'
wp post meta update "$ID" _regular_price 1200   # omit entirely if price unknown
wp post meta update "$ID" _price 1200
wp post meta update "$ID" _stock_status instock
wp post meta update "$ID" _manage_stock no
wp post meta update "$ID" _virtual no
wp post meta update "$ID" _downloadable no
wp post meta update "$ID" _product_attributes '{"%d0%be%d0%b1%d1%94%d0%bc":{"name":"Об&#039;єм","value":"30 мл","position":0,"is_visible":1,"is_variation":0,"is_taxonomy":0}}' --format=json
TID=$(wp media import ~/nawkiry-img/file.jpg --post_id="$ID" --title="..." --porcelain)
wp post meta update "$ID" _thumbnail_id "$TID"
```

Never invent a price. A product without a confirmed price stays a draft with no
`_regular_price` at all, and you report which ones need one.

Upload images first: `ssh ... 'mkdir -p ~/nawkiry-img'` then `scp -P 65002`.

## SEO (Yoast)

Yoast stores per-post meta and per-term meta. New products and new terms get
**nothing** automatically — always set these explicitly:

```bash
wp post meta update <id> _yoast_wpseo_focuskw "<focus keyphrase>"
wp post meta update <id> _yoast_wpseo_metadesc "<~155 chars>"
# taxonomy terms use term meta with the same keys, plus a title:
wp term meta update <term_id> _yoast_wpseo_focuskw "<keyphrase>"
wp term meta update <term_id> _yoast_wpseo_title "<Title> | HairZone"
wp term meta update <term_id> _yoast_wpseo_metadesc "<~155 chars>"
```

Audit instead of trusting that a write landed:

```bash
for id in $(wp term list product_cat --field=term_id); do
  n=$(wp term get product_cat $id --field=name)
  k=$(wp term meta get $id _yoast_wpseo_focuskw 2>/dev/null)
  d=$(wp term meta get $id _yoast_wpseo_metadesc 2>/dev/null)
  echo "$id|$n|KW=${k:-MISSING}|DESC=${d:-MISSING}"
done
```

`%%sitename%%` is a valid Yoast variable inside descriptions (existing products
use it).

## Diagnosing a site-wide 500

A white 500 on every URL is usually an **interrupted plugin update**, not a code
bug. `wp-cli` is the fastest oracle because it prints the fatal directly:

```bash
wp option get home          # prints the PHP fatal error with a stack trace
```

If the trace names a theme function calling a WooCommerce function
(e.g. `wc_get_page_permalink()` undefined in `astra-child/app/setup.php`), the
theme is fine — WooCommerce itself is **missing from disk** while still active
in the DB. Confirm and repair:

```bash
ls -d wp-content/plugins/woocommerce            # missing?
ls wp-content/upgrade/                          # staged new version, e.g. woocommerce.11.1.2
ls wp-content/upgrade-temp-backup/plugins/      # pre-update backup
```

WordPress moves the old plugin to `upgrade-temp-backup/` and unpacks the new one
in `upgrade/`; a crash between those steps leaves no plugin at all. Prefer the
staged **new** version if complete (check `grep -m1 'Version:'` and that
`woocommerce.php` exists), else restore the backup:

```bash
cp -a wp-content/upgrade/woocommerce.<ver>/woocommerce wp-content/plugins/woocommerce
# verify, then:
wp wc update                 # runs DB migration if needed
wp option get woocommerce_db_version
wp cache flush; wp litespeed-purge all
rm -rf wp-content/upgrade/woocommerce.<ver> wp-content/upgrade-temp-backup/plugins/woocommerce
```

Use `cp -a` (not `mv`) until the site returns 200, so a fallback remains.
Verify with real HTTP codes from outside, not just wp-cli:

```bash
for u in / /shop/ /product-category/shower-gels/; do
  curl -s -o /dev/null -w "$u %{http_code}\n" "https://hairzone.online$u"
done
```

`wp plugin list` needs `--skip-themes` while the theme still fatals.

A `create_autologin_<random>.php` in the webroot is Hostinger's hPanel one-click
WP-admin login, not malware — it 500s along with everything else.

## Current state reference

Category slugs (all English, names stay Ukrainian): `shower-gels`,
`body-scrubs`, `body-creams`, `liquid-hand-soaps`, `hand-creams`,
`intimate-care`, `bb-creams`, `toners`, `shampoos`, `conditioners`,
`hair-masks`, `leave-in-products`, `scalp-scrub-shampoos`,
`uncategorized-products`.

Na WKIR[y] pricing from the client price list: shower gels 1200, body
scrubs 1500, body creams 1500, intimate foam 1200. Hand creams (30 ml) and
liquid hand soaps (300 ml) had **no published price** — those stay drafts.

Product-type tags created alongside descriptive ones: `рідке мило`,
`крем для рук`, `інтимна гігієна`, `гель для душу`, `крем для тіла`.

Brand `count` only tallies published products, so drafts do not show up there.

Source assets and generator scripts live in `~/work/nawkiry/`
(`assets/`, `CATALOG.md`, `gen_products.py`).

## Reporting style

The user wants the result, not a narration of each command. Report what changed,
what is still blocked (e.g. missing prices), and any mistake you made and fixed
— do not quietly paper over a junk term or a partial run.
