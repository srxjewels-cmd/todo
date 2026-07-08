# [BRAND] — KPI Dashboard: Definitions, Formulas, Targets

Log every metric weekly in `kpi-tracker.csv` (one row per Monday). Phases:
- **Pre-launch** = Weeks 1–4 (2026-07-06 → 2026-08-02, incl. soft launch W4)
- **Launch month** = Weeks 5–8 (2026-08-03 → 2026-08-30)
- **Month 2** = from Week 9 (2026-08-31 →)

**Economic assumptions (update if SKU mix changes):**
- Gross margin ~75% on lab-diamond pieces; use 75% blended as the working number (vermeil margin is similar or better at these price points).
- Example SKU mix: vermeil pieces avg ~$140, lab-diamond pieces avg ~$495; expected order mix ~65% vermeil-led / 35% lab-led.

---

## 1. Sessions

**Definition:** Unique visits to the online store (a visitor can have multiple sessions).
**Pull from:** Shopify Admin → Analytics → overview tile "Online store sessions"; weekly detail in Analytics → Reports → **Sessions over time** (set date range Mon–Sun).

| Phase | Weekly target |
|---|---|
| Pre-launch (waitlist page) | 500 → 1,500/wk, growing weekly |
| Launch month | 3,000–6,000/wk |
| Month 2 | 5,000–8,000/wk |

Watch traffic *quality* too: sessions from paid should hold ≥ 1 min avg duration; if paid sessions bounce > 75%, the creative promise doesn't match the PDP.

---

## 2. Conversion Rate (CVR)

**Formula:** `CVR = orders ÷ sessions × 100`
**Benchmark:** demi-fine jewellery converts at **1–2.5%**; new brands start at the bottom of that band.
**Pull from:** Shopify Analytics → tile "Online store conversion rate" (also shows the funnel: added to cart → reached checkout → converted — diagnose which step leaks).

| Phase | Target |
|---|---|
| Pre-launch | n/a on store; track **waitlist opt-in rate** instead: signups ÷ landing sessions, target 15–30% from organic/social traffic |
| Launch month | 0.8–1.5% (soft-launch week will spike higher — it's warm list traffic; don't extrapolate) |
| Month 2 | 1.2–2.0%, trending to ≥ 1.5% |

If CVR < 0.8% for 2 consecutive weeks with ≥ 2,000 sessions: problem is site/offer, not traffic. Fix PDP/social proof before raising spend.

---

## 3. AOV (Average Order Value)

**Formula:** `AOV = total revenue ÷ total orders`
**Derived from SKU mix (worked example):**
`AOV ≈ (65% × $140 vermeil avg) + (35% × $495 lab avg) = $91 + $173 ≈ $264` → call the planning AOV **~$250** (founding discounts drag launch-month AOV down; multi-item orders push it up).
**Pull from:** Shopify Analytics → tile "Average order value"; sanity-check monthly in Reports → **Finance summary**.

| Phase | Target |
|---|---|
| Pre-launch (soft launch W4) | $200–240 (founding perk discount in effect) |
| Launch month | $220–260 |
| Month 2 | $240–280 (push with stack bundles + lab-hero ad angle) |

Track the lab-vs-vermeil order mix monthly (Shopify Reports → Sales by product) — AOV strategy = shifting mix, not raising prices.

---

## 4. CAC and the CAC Ceiling

**Formulas:**
- `Blended CAC = total ad spend ÷ total new-customer orders` (all orders in month 1–2 ≈ new)
- `Paid CAC = ad spend ÷ paid-attributed purchases` (per platform)
- **CAC ceiling (first-order break-even):** `AOV × gross margin = $250 × 0.75 ≈ $187`
  Above this you lose money on the first order even before overhead. Working rule: **spend ≤ 50% of ceiling** so the first order funds operations and the second order is profit.

**Pull from:** Ad spend = Meta Ads Manager column "Amount spent" + TikTok Ads Manager column "Cost". Orders = Shopify total orders. Paid purchases = Meta "Purchases" / TikTok "Payment completed" (expect platform over-attribution vs. Shopify — trust blended).

| Phase | Target |
|---|---|
| Pre-launch | ~$0 paid CAC (waitlist built organically; if running list-growth ads, ≤ $1.50/signup) |
| Launch month | Blended CAC ≤ $85–95; absolute ceiling $187 |
| Month 2 | Blended CAC ≤ $70–80 as creative + email compound |

---

## 5. ROAS and Break-even ROAS

**Formulas:**
- `ROAS = revenue attributed to ads ÷ ad spend` · `Blended ROAS = total revenue ÷ total ad spend`
- **Break-even ROAS = 1 ÷ gross margin = 1 ÷ 0.75 ≈ 1.33**
- More honest — contribution margin after payment fees (~3%), shipping subsidy, packaging (~7% combined): `1 ÷ 0.65 ≈ 1.54`. **Use 1.5 as the real floor.**

**Pull from:** Meta Ads Manager column "Purchase ROAS (return on ad spend)" (attribution: 7-day click, 1-day view); TikTok Ads Manager column "Complete payment ROAS"; blended = Shopify total sales ÷ (Meta spend + TikTok spend).

| Phase | Target (blended) |
|---|---|
| Pre-launch | n/a |
| Launch month | ≥ 1.33 floor, aim 1.5–2.0 while in learning |
| Month 2 | ≥ 2.0 (2.5+ = green light to scale spend 20–30%/wk) |

---

## 6. Waitlist Size & List-to-Customer Conversion

**Formulas:** `Waitlist size = subscribers in the "[BRAND] Waitlist" Klaviyo list` · `List-to-customer = founding-window orders from list members ÷ waitlist size × 100`
**Benchmark:** a warm, well-nurtured pre-launch list converts **5–15%** in the founding window.
**Pull from:** Klaviyo → Audience → **Lists & segments** → waitlist list → growth chart; conversion via Klaviyo launch-flow "Placed Order" conversions or a Shopify segment of customers whose email is on the list.

| Phase | Target |
|---|---|
| Pre-launch | ≥ 400 by end W2 → ≥ 1,000 by end W3 → **1,500–2,500 at soft launch** |
| Launch month (W4 window) | 5–15% list-to-customer → 75–375 founding orders (plan case: ~8% ≈ 120–200) |
| Month 2 | Keep list growing ≥ 500/mo; ongoing list buyer rate ≥ 1.5%/mo |

---

## 7. Creator Seeding: Post Rate

**Formula:** `Post rate = creators who posted ÷ boxes shipped × 100` (cumulative; allow a 2-week lag after shipment before counting a box as "no post")
**Benchmark:** well-targeted gifting yields **20–40%** post rate.
**Pull from:** manual creator tracker sheet (`../07-creators/`) — log every tag, mention, and story; check IG tagged/mentions and TikTok brand search twice a week (delegatable).

| Phase | Target |
|---|---|
| Pre-launch | 50 boxes W2 → 100–125 by W3; post rate ≥ 20% (≥ 10 posts from wave 1) |
| Launch month | Cumulative 250 boxes by W8; lifetime post rate 20–30% (50–75 posts) |
| Month 2 | ~50 boxes/mo top-up; post rate ≥ 30% (better targeting from data) |

If post rate < 15% after wave 2: fix targeting (smaller creators post more) and the unboxing moment before shipping more.

---

## 8. Vanity-Code Usage

**Formula:** `Code share of orders = orders using any creator code ÷ total orders × 100`; also `Revenue per box = creator-code revenue ÷ boxes shipped`
**Pull from:** Shopify Analytics → Reports → **Sales by discount** (revenue + order count per code); quick counts on the Discounts page. Roll up all creator codes weekly into `code_uses` in the tracker.

| Phase | Target |
|---|---|
| Pre-launch | Codes created + logged for 100% of shipped boxes; first redemptions during soft launch |
| Launch month | Creator codes on 10–20% of orders |
| Month 2 | Revenue per box shipped ≥ 1× landed box cost (seeding self-funding); top-10 codes → affiliate tier |

---

## 9. Email Revenue Share

**Formula:** `Email revenue share = Klaviyo-attributed revenue (flows + campaigns) ÷ total Shopify revenue × 100`
**Benchmark target:** **20–30%** of revenue from email at steady state.
**Pull from:** Klaviyo → Dashboard → "Attributed revenue" (or Analytics → Business review); divide by Shopify Analytics "Total sales" for the same Mon–Sun range. Keep Klaviyo attribution at its default (5-day email click/open) and be consistent.

| Phase | Target |
|---|---|
| Pre-launch | n/a (build the flows: welcome, launch sequence, post-purchase, abandon) |
| Launch month | 25–40% (launch is list-driven — this is normal, it will settle) |
| Month 2 | 20–30% steady state; flows ≥ half of email revenue |

---

## Target summary table

| KPI | Pre-launch | Launch month | Month 2 |
|---|---|---|---|
| Sessions/wk | 500–1,500 (landing) | 3,000–6,000 | 5,000–8,000 |
| CVR | 15–30% waitlist opt-in | 0.8–1.5% | 1.2–2.0% |
| AOV | $200–240 (soft launch) | $220–260 | $240–280 |
| Blended CAC | ~$0 | ≤ $85–95 (ceiling $187) | ≤ $70–80 |
| Blended ROAS | n/a | ≥ 1.33, aim 1.5–2.0 | ≥ 2.0 |
| Waitlist | 1,500–2,500 by soft launch | 5–15% list→customer | +500/mo growth |
| Boxes / post rate | 100–125 / ≥ 20% | 250 cum. / 20–30% | +50/mo / ≥ 30% |
| Code share of orders | first uses | 10–20% | rev/box ≥ box cost |
| Email rev share | n/a | 25–40% | 20–30% |

---

## The 30-Minute Monday Review Ritual

Every Monday, 9:00–9:30, starting Week 4 (soft launch) at the latest. One tab open per source. Output = one filled row in `kpi-tracker.csv` + one decision.

**Minutes 0–10 — Pull the numbers (set every date range to last Mon–Sun):**
1. Shopify Analytics overview: sessions, conversion rate, total sales, orders, AOV → columns `sessions, conversion_rate, orders, revenue, aov`
2. Shopify Reports → Sales by discount: sum creator-code orders → `code_uses`
3. Meta Ads Manager (columns: Amount spent, Purchases, Cost per purchase, Purchase ROAS) + TikTok Ads Manager (Cost, Payment completed, Complete payment ROAS): sum spend → `ad_spend`; compute blended `cac = ad_spend ÷ orders`, `roas = revenue ÷ ad_spend`
4. Klaviyo: waitlist list size → `waitlist_size`; attributed revenue ÷ Shopify revenue → `email_revenue_share`
5. Creator tracker: cumulative boxes + posts → `boxes_shipped, creator_posts, post_rate`

**Minutes 10–20 — Diagnose (against the phase targets above):**
- Traffic problem (sessions down)? Conversion problem (CVR below band)? Economics problem (CAC > target, ROAS < 1.5)? List problem (waitlist/email share stalling)? Seeding problem (post rate < 20%)?
- Write one sentence in the `notes` column: the single biggest constraint this week.

**Minutes 20–30 — Decide ONE lever and assign it:**
- Pick exactly one primary action (e.g., "kill bottom-half creatives + brief 8 new hooks" or "ship PDP social-proof block" or "re-target seeding list to <50k creators"). One owner, done-by date. Multiple small tweaks beat zero; but one big lever beats five tweaks.
- 2-min ops check: made-to-order queue on time? Any support fire? Then stop — 30 minutes, done.
