# Your own SRX DIAMONDS storefront

This folder lets you run the Quince‑style storefront on **your own products** — your
photos, your descriptions, your prices. Same engine that powers the live demo (filters,
sort, colour/carat photo‑swap, price‑compare, WhatsApp checkout, geo‑currency), but the
content is 100% yours.

## Quick start
```bash
# 1) generate the placeholder sample (fake products + auto‑drawn photos) to see the format
python catalog/make_sample.py

# 2) build the store from a catalog file
python build_quince_shop.py catalog/sample_catalog.json \
    --out catalog/index.html --brand "SRX DIAMONDS" --whatsapp 919723891732

# 3) open catalog/index.html in a browser
```
To make it yours: edit `sample_catalog.json` (or generate the same shape from your own
data), replace the placeholder images under `catalog/photos/` with your real photos, rebuild.

## Catalog format (`sample_catalog.json`)
A JSON list of products. Each product:

```jsonc
{
  "id": "SRX-001",                       // any unique id (used as the WhatsApp reference)
  "cat": "Engagement Rings",             // category tab: Necklaces / Bracelets / Rings / Engagement Rings / Earrings
  "name": "Round Solitaire Engagement Ring",
  "details": "- point one\n- point two", // shown in the DETAILS accordion (\n = new line)
  "rating": 4.9,                          // optional; shows the star + count on card/PDP
  "reviews": 214,                         // optional
  "materials": ["Lab Grown Diamond","14k Gold","Platinum"],  // drives the Material filter
  "options": [ /* see below */ ],
  "variants": [ /* see below */ ]
}
```

### options
Each option is a chooser shown on the product page. Types: `swatch` (colour circles) or
`select` (buttons).
```jsonc
{"name":"Color","type":"swatch","values":[
   {"label":"Yellow Gold","hex":"#E6C46A","q":"Yellow"},   // hex = swatch colour; q = which Color filter it counts under
   {"label":"White Gold","hex":"#E5E5E8","q":"White"}
]}
{"name":"Center Carat Weight","type":"select","values":[{"label":"1"},{"label":"1.5"},{"label":"2"},{"label":"3"}]}
{"name":"Size","type":"select","values":[{"label":"6"},{"label":"6.5"},{"label":"7"}]}
```
- An option named **`Carat`** or **`Center Carat Weight`** automatically powers the **Carat
  filter** in the toolbar/drawer, and changing it swaps the gallery + price on the product page.
- `q` values map to the Color filter swatches: `Yellow, Grey, White, Pink, Red, Blue, Green,
  Brown, Tan`.

### variants
One entry per real, orderable combination. `sel` names the option values it corresponds to.
```jsonc
{
  "sel": {"Color":"Yellow Gold","Center Carat Weight":"3"},  // must match option labels above
  "usd": 3900,                 // your price in USD (auto‑converts to the visitor's currency)
  "orig": 9360,                // optional "compare at" price -> strike‑through + "Save $X (Y% off)"
  "imgs": ["photos/SRX-001/yellow-gold-3/1.jpg","photos/SRX-001/yellow-gold-3/2.jpg"],
  "thumb": "photos/SRX-001/yellow-gold-3/1_t.jpg"            // small card image
}
```
Notes:
- Give **each colour × carat its own `imgs`** so the photos change when the shopper switches
  colour or carat (that's the "different in hand" effect).
- `thumb` is the small grid image. For the gallery, the engine looks for a `_t.jpg` next to each
  full image (e.g. `1.jpg` → `1_t.jpg`); include those, or reuse the full images.
- An option with **no** matching `sel` on any variant (e.g. ring **Size**) is treated as a free
  choice — always selectable, and added to the WhatsApp message.

## Deploy
Put `index.html` + `photos/` on any static host (GitHub Pages, Netlify, etc.). Keep photos as
**relative paths** so they load from the same origin.

## Photos & copy
These placeholders are auto‑drawn shapes. Replace them with **your own product photography and
descriptions** — that's what makes it your store and yours to promote.
