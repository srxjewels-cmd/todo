# [BRAND] — Pixel, Conversions API & Catalog Setup (Shopify → Meta + TikTok)

**Owner:** Founder / whoever holds Business Manager + TikTok Business Center admin
**Prereqs before starting:** live Shopify store (password page is fine), Meta Business Manager with admin access, a Facebook Page + Instagram account for [BRAND], TikTok Business Center + TikTok Ads Manager account, and a published RIV-01 product page.
**Time estimate:** 60–90 min for both platforms, plus 24–48h for events/catalog to fully validate.

---

## 1. Why the Conversions API (CAPI) matters — read this first

Since iOS 14.5 (April 2021, App Tracking Transparency), a large share of iPhone users opt out of tracking. Browser-side pixels alone now miss a meaningful chunk of purchases because:

- Safari/iOS ITP truncates cookie lifetime and blocks third-party cookies entirely.
- Ad blockers and privacy browsers block the pixel script outright.
- Opted-out iOS users send no browser events at all.

**The Conversions API sends the same events server-to-server from Shopify's backend to Meta**, bypassing the browser. Meta deduplicates browser + server events (via a shared `event_id`), so you don't double count — you just recover the events the pixel missed.

Practical impact for a new brand: better-attributed purchases → the algorithm exits learning phase faster on a small budget → lower CAC. For a jewellery brand at higher AOV with fewer conversions per day, **every recovered purchase event materially improves optimisation**. Do not launch ads without CAPI active.

The good news: **Shopify's official "Facebook & Instagram" app implements both the pixel and CAPI for you.** No code, no Zapier, no third-party CAPI apps needed.

---

## 2. Meta: pixel + CAPI via Shopify's Facebook & Instagram app

### 2.1 Create the assets in Meta (if not already done)

1. Go to **business.facebook.com → Settings (gear icon) → Business Settings**.
2. Under **Accounts → Pages**, confirm the [BRAND] Facebook Page exists and you're an admin.
3. Under **Accounts → Instagram accounts**, connect the [BRAND] IG account.
4. Under **Accounts → Ad accounts**, create/claim the ad account. Set currency + timezone carefully — **these cannot be changed later** (pick the currency you'll report P&L in; USD if US-led).
5. Under **Data sources → Datasets (Pixels)**: you can pre-create a dataset named `[BRAND] Pixel`, or let the Shopify app create one during setup (letting the app create it is simplest).
6. **Verify your domain:** Business Settings → **Brand safety and suitability → Domains** → Add → enter your store domain (the custom domain, e.g. `yourbrand.com`, not `*.myshopify.com`) → choose **Meta-tag verification** → copy the meta tag → in Shopify: **Online Store → Themes → Edit code → theme.liquid**, paste inside `<head>` → back in Meta, click **Verify**. (DNS TXT verification also works if you prefer.)

### 2.2 Install and configure the Shopify app

1. In Shopify admin: **Settings → Apps and sales channels → Shopify App Store** → search **"Facebook & Instagram"** (by Meta/Shopify) → **Install**.
2. Open the app → **Start setup** → **Connect account** → log in with the Facebook profile that has admin rights on the Business Manager.
3. Walk the connect flow, selecting in order:
   - **Business portfolio:** the [BRAND] Business Manager.
   - **Facebook Page:** [BRAND] page.
   - **Instagram account:** [BRAND] IG.
   - **Ad account:** the [BRAND] ad account.
   - **Pixel/Dataset:** select the existing `[BRAND] Pixel` or create new.
4. **Data sharing settings — the critical screen.** Choose **Maximum**.
   - *Standard* = browser pixel only.
   - *Enhanced* = pixel + Advanced Matching (hashed email/phone attached to events).
   - **Maximum = pixel + Advanced Matching + Conversions API (server-side).** This is the whole point. Select Maximum.
5. Accept Meta's terms, finish the flow. The app now injects the pixel on every storefront page **and** streams server events (including Purchase from Shopify's checkout, which the browser pixel often misses) with automatic deduplication.
6. Sanity check: in the app's **Settings** tab you should see the connected pixel ID, data sharing = Maximum, and (once you enable it in §4) the catalog sync status.

> **Do NOT also paste the pixel base code into theme.liquid or add a second pixel via another app.** Double-firing inflates events and confuses optimisation. One integration path only.

### 2.3 Verify CAPI is actually flowing

1. **Meta Events Manager** (business.facebook.com/events_manager2) → select the pixel → **Overview**.
2. Under each event (PageView, ViewContent, etc.), check **Connection method**: you want to see **"Browser · Server"** on events within ~30 min of traffic. Purchase may show Server-dominant — that's correct.
3. Open **Diagnostics** tab — resolve anything flagged (common: domain not verified → do §2.1 step 6).
4. Check **Event Match Quality (EMQ)** per event after a day or two of traffic: aim for **6.0+ ("Good")** on Purchase. Shopify's Maximum setting passes hashed email, which usually gets you there.

---

## 3. TikTok: pixel + Events API via the TikTok Shopify app

1. In Shopify admin: **Apps → Shopify App Store** → search **"TikTok"** (official app by TikTok Inc.) → **Install**.
2. Open the app → **Set up now** under TikTok for Business → **Connect** your TikTok Business Center / TikTok Ads Manager login.
3. Select or create:
   - **Business Center:** [BRAND].
   - **Ad account:** [BRAND] ad account (again — currency + timezone are permanent).
   - **TikTok account:** the organic @[BRAND] handle (optional but connect it — enables Spark Ads later, which you'll want for creator content).
4. **Data sharing level:** choose **Enhanced** or **Maximum** (naming varies by app version — pick the highest tier offered). The top tier enables **Advanced Matching + Events API (TikTok's server-side equivalent of CAPI)**, same logic as Meta: recover events lost to iOS/ad-blockers.
5. The app creates a TikTok pixel automatically and injects it storefront-wide. Note the pixel ID shown in the app.
6. Verify in **TikTok Ads Manager → Tools → Events → Web Events → [your pixel] → Overview**: events should appear within ~30 min of test traffic. Check that events show both browser and server ("API") channels if the diagnostics view breaks it out.
7. Optional but recommended: install the **TikTok Pixel Helper** Chrome extension for spot checks (same workflow as Meta Pixel Helper below).

---

## 4. Event verification checklist (both platforms)

Run this **end-to-end test purchase** before spending $1 on ads. Use a real card and refund yourself, or a 100%-off draft order won't fire value data — better: set up **Shopify's Bogus Gateway is not available on live plans**, so do a real $1 test product purchase or a real RIV-01 purchase you refund.

### 4.1 Test method — Meta

1. **Events Manager → your pixel → Test events** tab.
2. In the **"Test browser events"** box, it gives you a session — open your store **in the same browser** (or paste your store URL in the field provided) so your session is tagged.
3. Walk the funnel and confirm each event appears in the Test Events stream **in real time**, with correct parameters:

| Step you perform | Event expected | Parameters to verify |
|---|---|---|
| Land on homepage | `PageView` | — |
| Open RIV-01 product page | `ViewContent` | `content_ids` = Shopify variant/product ID, `content_type=product`, `value`, `currency` |
| Click Add to Cart | `AddToCart` | `content_ids`, `value`, `currency` |
| Click Checkout | `InitiateCheckout` | `value`, `currency`, `num_items` |
| Complete payment | `Purchase` | `value` = order total, `currency`, `content_ids` |

4. For **server events**: in the Shopify Facebook & Instagram app there's a **test event code** field under settings (or use the code shown in Meta's Test Events tab, format `TEST12345`) — paste it into the app so server events also route to the test stream. Confirm Purchase arrives via **Server** channel too.
5. **Deduplication check:** in Test Events, browser + server versions of the same event should show as deduplicated (one processed event). If you see doubled Purchases in Overview after 24h, you have a second pixel installed somewhere — hunt it down (theme.liquid, other apps, old Google Tag Manager container).
6. Install **Meta Pixel Helper** (Chrome extension) and browse the store — it should show exactly **one** pixel ID firing per page.

### 4.2 Test method — TikTok

1. **TikTok Ads Manager → Tools → Events → Web Events → your pixel → Test Events** tab.
2. Options: browse your site with the **TikTok Pixel Helper** extension active, or use the QR-code/test-flow TikTok provides in the Test Events tab.
3. Verify the same funnel: `Pageview` (automatic), `ViewContent`, `AddToCart`, `InitiateCheckout`, `CompletePayment` (TikTok's name for Purchase) — TikTok event names differ slightly; the Shopify app maps them for you.
4. Confirm `value` and `currency` populate on `CompletePayment` — without value data you can't optimise for purchase value or compute true ROAS in-platform.

### 4.3 Sign-off checklist (print this)

- [ ] Meta pixel fires once (Pixel Helper shows 1 pixel ID)
- [ ] Meta: all 5 events verified in Test Events with `value`/`currency`/`content_ids`
- [ ] Meta: events show **Browser · Server** connection method (CAPI live)
- [ ] Meta: deduplication confirmed (no doubled Purchases)
- [ ] Meta: domain verified, no open Diagnostics errors
- [ ] Meta: EMQ ≥ 6 on Purchase (check after 48h of traffic)
- [ ] TikTok: all events verified incl. `CompletePayment` with value
- [ ] TikTok: Events API / server channel active
- [ ] Test purchase refunded, test orders tagged/archived in Shopify

---

## 5. Product catalog / feed setup

### 5.1 Meta catalog (from the same Shopify app)

1. In the Shopify **Facebook & Instagram** app → **Settings** → ensure a **catalog** is connected (the app auto-creates one and syncs your Shopify products; sync runs continuously).
2. Control **which** products sync: in Shopify, each product's **Publishing / Sales channels** section must include the Facebook & Instagram channel. Only publish launch-ready SKUs (RIV-01, studs) — unpublish drafts/placeholders.
3. In **Meta Commerce Manager** (business.facebook.com/commerce) → your catalog → **Items**: confirm RIV-01 and studs appear with correct price, image, availability, and link to your domain.
4. Fix any **Issues** flagged (missing GTIN warnings are acceptable for made-to-order jewellery — you can mark items as custom/no-GTIN; missing images or prices are not acceptable).
5. Catalog → **Event data sources**: confirm your pixel is paired to the catalog (the app does this; verify). This is what powers Advantage+ Catalog (DPA) retargeting later — "viewed RIV-01, didn't buy" ads.
6. Made-to-order note: keep Shopify inventory policy set so items are always purchasable ("Continue selling when out of stock" ON, or track no inventory) — otherwise the catalog flips to "out of stock" and catalog ads stop serving.

### 5.2 TikTok catalog

1. TikTok Shopify app → **Catalog** section → enable product sync (auto-creates a catalog in TikTok Business Center tied to your ad account).
2. Same channel-publishing logic: only launch SKUs.
3. Verify in **TikTok Business Center → Assets → Catalogs**: products present, images/prices/links correct, no disapprovals.
4. TikTok reviews catalog items against its ad policies — jewellery is fine, but ensure no medical/income claims in descriptions and that "lab-grown diamond" wording (below) is used so items aren't flagged as misleading "diamond" claims.

### 5.3 Catalog hygiene for jewellery (both platforms)

**Titles — formula (max ~65 chars visible; front-load what matters):**

```
[BRAND] · {Style} — Lab-Grown Diamond {Product Type} · {Metal}
```

Examples:
- `[BRAND] · RIV-01 Rivière — Lab-Grown Diamond Necklace · 18k Gold Vermeil`
- `[BRAND] · Solitaire Studs — Lab-Grown Diamond Earrings · 18k Gold Vermeil`

Rules:
- **COMPLIANCE (non-negotiable): "Lab-Grown" immediately precedes "Diamond" everywhere** — titles, descriptions, custom labels. Never "diamond necklace (lab-grown)", never "lab diamond", never "diamond" standing alone. This mirrors FTC Jewelry Guides (§23.12 et seq.) and UK CAP/ASA expectations: unqualified "diamond" implies mined.
- **Vermeil claims must state base metal + thickness:** write "18k gold vermeil (2.5µm+ gold over sterling silver)" in every description. Never "gold necklace", never "solid gold", never vermeil without the sterling-silver base disclosed. (US FTC requires ≥2.5µm gold over sterling for "vermeil" — you meet it; say so.)
- Include total carat weight where known: "0.50 tcw" etc. If stones are certified, "IGI-certified" may appear in the description — keep certificate claims literally true (which stones/sizes carry certs).
- No ALL CAPS, no emoji, no "SALE/DEAL/% OFF" (brand rule: no discount language — also true in `sale_price` fields: **don't use them**).

**Descriptions (first 150 chars do the work):**

```
{Product}. IGI-certified lab-grown diamonds set in 18k gold vermeil
(2.5µm+ gold over sterling silver). Made to order for you — ships in
~7 days. Real diamonds, honestly priced.
```

**Images — ratio and crop rules:**
- **Primary catalog image: 1:1 square, minimum 1024×1024 px** (Meta minimum is 500×500; TikTok similar — ship 1500×1500 so zoom-crops survive).
- Product on **clean, consistent background** (soft neutral — quiet-luxury; pure white is acceptable but keep it uniform across all SKUs so the catalog grid looks like one brand).
- **Fill 70–80% of frame with the product**; centre it; no tight crops that amputate the clasp or ear post. Catalog placements auto-crop to 1:1 and sometimes 4:5/9:16 — keep critical detail in the central safe zone.
- **No text, logos, watermarks, or price overlays on catalog images** (Meta can reject; it also looks like discount retail — off-brand).
- Additional images per product: on-model shot (neck/ear), macro sparkle detail, scale shot. Shopify syncs all product images; the first is the catalog hero.
- Jewellery-specific: shoot with controlled directional light so the lab-grown diamond reads as bright but not blown-out; avoid heavy retouching that misrepresents stone size (misleading-imagery risk under ASA/FTC).

**Custom labels (Meta) / categories:** set `custom_label_0 = hero` on RIV-01 and `custom_label_0 = support` on studs via the app's field mapping or Shopify tags — lets you build catalog ad sets around the hero later. Set Google product category to `Apparel & Accessories > Jewelry > Necklaces` / `> Earrings` for cleaner platform categorisation.

---

## 6. Consent / GDPR cookie banner for UK & EU traffic

You are selling into the UK/EU, so **GDPR + UK GDPR + ePrivacy apply: marketing pixels may only fire after opt-in consent** for visitors in those regions. Doing this wrong risks fines and — practically — Meta/TikTok will increasingly discard EU events sent without a consent signal.

Setup (Shopify-native, no extra app required to start):

1. **Shopify admin → Settings → Customer privacy** (formerly Customer Privacy / Cookie banner).
2. **Enable the cookie banner** and set region visibility to **EEA + UK** (you can leave US on "collect before consent" or enable a lighter US state-privacy banner for CA/CO/etc. — recommended: enable for US states with privacy laws too).
3. Set data collection for EEA/UK to **"Collected after consent"** (this makes Shopify's Customer Privacy API gate the Meta and TikTok apps' pixels — both official apps respect it automatically; this is a big reason to use the official apps rather than manual pixel code).
4. Customise banner text/colours to match brand (quiet, minimal, no dark patterns — **Reject must be as easy as Accept**, one click each; required by EU regulators and ICO guidance).
5. Publish a **cookie/privacy policy page** listing Meta and TikTok as advertising partners and covering server-side (CAPI/Events API) sharing of hashed email for ad measurement.
6. **Test:** open the site via a UK/EU VPN in a fresh incognito window → confirm with Pixel Helper that **no Meta/TikTok events fire before consent**, and that events fire after clicking Accept. Click Reject → confirm continued silence.
7. Expect the trade-off: EU/UK event volume will undercount vs. US. That's correct behaviour, not a bug. CAPI does **not** bypass consent — consent state gates server events too.
8. If you later want granular Consent Mode-style banners (categories, per-vendor toggles), add a CMP app (e.g. Pandectes, Consentmo) — but Shopify's native banner is sufficient and correctly integrated at launch.

---

## 7. Order of operations (launch week)

1. Domain verified in Meta (§2.1) → 2. FB&IG app installed, data sharing **Maximum** (§2.2) → 3. TikTok app installed, top data tier (§3) → 4. Cookie banner live and tested (§6) → 5. Full-funnel test purchase on both platforms (§4) → 6. Catalogs verified clean (§5) → 7. Let 48h of organic/waitlist traffic season the pixels → 8. Launch campaigns per `/home/user/todo/launch/08-ads/ad-concepts.md`.
