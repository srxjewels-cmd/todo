# Execution 2 — parked plan

Trigger: when the user says **"let's do execution 2"**, resume this.

## Goal (user's words)
> new goal: scrape full jewellery section (that says lab) in proper form with photos of every
> size option and each photo of every size, every section details and comparison and every
> detail in it — in the details so that in the future I want you to use it.

Decoded — scrape the **full Quince lab‑grown jewelry section** (everywhere it says "lab" /
lab‑grown) into a **proper structured catalog** for future use by the SRX DIAMONDS storefront
engine, capturing **every detail**:

- **Every category** of lab‑grown diamond jewelry (necklaces, bracelets, rings, engagement
  rings, wedding bands, earrings/studs/hoops/huggies, pendants, tennis, etc.) — not just the
  four `-all` pages currently used.
- **Photos for every option, per option value** — in particular a photo set **per size /
  per carat**, e.g. "Center Carat Weight" 1 / 1.5 / 2 / 3 / 5 each has its own in‑hand shots
  (different carats look different on the hand). Colour × carat × (size) each carry their own
  gallery.
- **Every option**, with its real Quince name & type: Color (swatch+hex), **Center Carat
  Weight**, Ring Size, Length, Metal, etc. (Currently the scraper lumps non‑Color options into
  "Size" and only detects total‑ctw from the title — this must be fixed to capture the real
  per‑product option matrix.)
- **Price comparison** for every piece: Quince price vs `traditionalRetailPrice`
  ("Compare at" / "you save"), plus any price‑breakdown / "the difference" data.
- **Every section's details**: full description/details text, specs (carat, metal, dimensions,
  production), **rating + review count** (and reviews if wanted), badges (new / back in stock).

## Deliverable
A committed, structured dataset (`shopdata/variants.json` v2 + `docs/photos/...` per option
value) that the storefront engine consumes, exposing: Carat / Center Carat Weight **filter**
in the rail (esp. on rings), per‑carat & per‑colour photo swap on the PDP, price‑compare block,
full details — desktop + mobile, matching Quince's jewelry UX.

## Storefront features to build/finish (functional — fine to do)
- Add **Carat / Center Carat Weight filter** to the filter bar + drawer (dynamic per category).
- PDP **Center Carat Weight** selector using real values; changing it swaps the gallery + price.
- **Price‑compare** UI (compare‑at strike + "Save $X" + savings %).
- Keep: filters, sort, grid, geo‑currency, WhatsApp enquiry, SRX DIAMONDS branding.

## Technical starting points (already in this repo/branch)
- `scrape_variants.py` — current scraper (needs the option‑matrix rework above).
- `build_quince_shop.py` — the storefront engine (Quince‑style; add the Carat filter + Center
  Carat Weight PDP + price‑compare).
- Pipeline: GitHub Actions (`.github/workflows/quince-scrape.yml`, `workflow_dispatch`, input
  `scrape=true|false`) runs the scrape/build on a runner (the sandbox can't reach Quince), then
  publishes `docs/` to branch `claude/shop-pages` → GitHub Pages at
  https://srxjewels-cmd.github.io/todo/ . `raw.githubusercontent.com` is reachable for verifying.
- Quince data lives in each product page's `__NEXT_DATA__` →
  `props.pageProps.pageData.context.pageDataJson.product` (fields: title, slug, productOptions,
  new_color_options[hexCode], variants[options,price,traditionalRetailPrice], images[options
  tagged by Color/…], details, rating). Category listing slugs already carry the `women/` prefix.
- A read‑only probe of the ring "Center Carat Weight" option + per‑category facets was started;
  re‑run it first to model the option matrix correctly.
