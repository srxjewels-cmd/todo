# [BRAND] — Creator Gifting SOP (Seeding Program)

**Owner:** Founder
**Last updated:** 2026-07-08
**Works with:** `outreach-templates.md` + `seeding-tracker.csv`
**Program shape:** gifting-only, zero posting obligation, gift-with-purchase attribution (never % off).

---

## 1. Seeding box spec

Every box is identical in structure; only the hero piece changes. Target: feels like a $300+ unboxing, costs a fraction of that above COGS.

### Contents (in unboxing order)

| # | Item | Spec | Target unit cost |
|---|------|------|------------------|
| 1 | Outer shipper | Plain rigid kraft or matte mailer, discreet — no branding shouting "jewellery inside" (theft + quiet-luxury) | $1.50–2.50 |
| 2 | Inner gift box | Rigid two-piece or magnetic-closure box, matte, brand colour, blind-debossed logo (no foil, no gloss) | $3.00–5.00 |
| 3 | **Hero piece** | One SKU **matched to the creator's aesthetic and tier** (see §2). Nestled in recycled-cotton or FSC tissue + branded microfibre pouch | COGS $18–45 by SKU |
| 4 | IGI certificate card | The piece's actual IGI report card (lab-grown diamond certification) — this is the proof-of-substance moment; don't bury it | in COGS |
| 5 | Insert card | A6, uncoated heavy stock. Front: one line of brand story ("Made to order. Priced fairly, forever."). Back: **QR code to shop + their unique vanity code** (`[FIRSTNAME]` / [brand].com/[firstname]) and one line: "This code gives your people our founding-customer gift with their order — never a discount, because our prices don't need one." | $0.40–0.80 |
| 6 | Handwritten-style note | A6 flat card, real pen if volume allows (<15/week: founder handwrites; above: premium handwriting-style print, but sign each by hand). 2–3 sentences, references the same specific post from outreach. Never generic. | $0.30–0.60 |
| 7 | Care card | Vermeil care in 4 lines (no water, no perfume, pouch storage, soft cloth) | $0.20 |

**Packaging target (everything except the piece): $6–10 per box.**
**All-in seeded box target: $30–60** (studs/huggies tiers) / **$50–75** (pendant/Riviere tiers), including COGS + packaging + domestic ship. International (UK/EU) add $10–20 tracked + DDP where feasible — creators must never pay customs on a gift.

**Never in the box:** discount language, posting instructions, hashtags "we'd love you to use," shot lists, usage-rights forms. One disclosure line only (see §3).

---

## 2. Tier logic by follower band

Fit beats follower count. "High-fit" = aesthetic match (quiet luxury, minimal, warm-neutral palettes), audience 25–40 W in US/UK/EU, real engagement (≥2–3% ER, human comments), no pod behaviour, no discount-code-spam grid.

| Tier | Follower band | Gift | SKUs | Rationale |
|------|--------------|------|------|-----------|
| T1 | 3–10K (nano) | Studs **or** huggies | STU-01, STU-02, HUG-01, HUG-02 | Highest post rates, lowest COGS, best cost-per-post. Volume tier. |
| T2 | 10–25K (micro) | Pendant | PEN-01, PEN-02 | Neck pieces shoot better in reels; mid COGS for mid reach. |
| T3 | 25–50K, **high-fit only** | Riviere necklace | RIV-01 | Hero SKU reserved for creators whose grid could be our campaign. Founder signs off each T3 send personally. |
| — | Any band | **Never seeded** | HALO-SP-01 | Natural halo — too expensive to seed. Loan-only for paid campaigns, if ever. |

**Within-tier matching:** pick the specific SKU by the creator's visible style — e.g. gold-heavy minimalist grid → HUG-01; delicate/layering content → PEN-02. Log the choice + why in tracker notes.

**Overrides:** a 60K creator with perfect fit and modest rates may be worth a T3 send; a 40K creator with pod-y engagement gets nothing. Founder judgment, documented in notes.

---

## 3. Disclosure — FTC (US) + ASA/CMA (UK) + EU

We say this to every creator at the "yes" stage and again with tracking info. Standard line:

> "One thing we always ask: if you choose to post, please disclose the gift clearly — #gifted, 'gifted', or your platform's paid-partnership/ad label, per FTC and UK ASA rules. Always, every time, even in Stories. We'd never want it any other way."

What we hold ourselves to:

- **US (FTC):** a free product creates a "material connection" — creator must disclose clearly and conspicuously, in the post itself (not buried in a hashtag wall or "more" fold). #gifted or "gift from [BRAND]" up front.
- **UK (ASA/CMA):** gifted product = incentive; if the brand had any input, content likely needs "Ad." Even pure no-strings gifts should be labelled #gifted/#ad per current ASA guidance. UK creators should default to **"Ad"** if unsure.
- **EU:** similar consumer-protection rules across member states; #gifted / "Werbung" / "publicité" per local norms — creator's local rules govern, our ask is simply "disclose, always."
- **Our side:** we never discourage disclosure, never suggest it's optional, and we do not reshare creator content that lacks disclosure until it's fixed. If we spot a missing disclosure, we send one friendly note asking them to add it.

---

## 4. Tracking workflow — `seeding-tracker.csv`

One row per creator. Status field is the single source of truth; every status change gets a date.

**Suggested columns:** `handle, first_name, platform, followers, tier, fit_notes, status, status_date, first_touch_date, followup1_date, followup2_date, sku, vanity_code, vanity_url, address_received, ship_date, tracking_no, delivered_date, posted_date, post_url, disclosure_ok, code_redemptions, notes`

### Status pipeline + exit criteria

| Status | Meaning | Moves forward when |
|--------|---------|--------------------|
| `to_review` | Sourced, not yet vetted | Fit check passed (aesthetic, audience, engagement, no pods) → `to_contact`. Failed → row kept, notes "rejected — [reason]" |
| `to_contact` | Vetted, personalisation slot fillable | First-touch DM/email sent → `contacted` (log date + channel) |
| `contacted` | In outreach sequence (max 3 touches per `outreach-templates.md`) | Yes → `agreed`. Decline or 3 touches + silence → stays `contacted`, notes closed |
| `agreed` | Said yes; collecting address, assigning SKU + vanity code/URL | Box shipped, tracking logged → `shipped` |
| `shipped` | In transit / delivered | Content spotted → `posted` (log URL, date, disclosure_ok). Set a +14-day check after delivery — if nothing, note "delivered, no post" and **do nothing** (no chasing; gift means gift) |
| `posted` | Live content exists | Terminal for seeding. Feeds §6 re-engagement review |

### At `agreed`, before shipping (checklist)

- [ ] Address + phone collected
- [ ] SKU confirmed against tier table (§2); T3 founder-approved
- [ ] Vanity code created in Shopify (`FIRSTNAME`, gift-with-purchase — **not a discount**) and tested
- [ ] Vanity URL redirect live and tested
- [ ] Insert card printed with their code/QR; handwritten note references their actual content
- [ ] Disclosure line sent in the confirmation message
- [ ] Tracker row fully populated

---

## 5. Weekly cadence + cost model

### Weekly operating rhythm (founder, ~3–4 hrs/week)

| Day | Block | Action |
|-----|-------|--------|
| Mon | 45 min | Source 10–15 new creators → `to_review`; vet last week's → `to_contact` |
| Tue | 45 min | Send 8–12 first-touches; send due follow-up 1s and 2s (5–7 / 10–14 day clocks) |
| Wed | 30 min | Process yeses: addresses, codes, URLs, SKU match → `agreed` |
| Thu | 60 min | Pack + ship all `agreed` boxes; write notes; log tracking → `shipped` |
| Fri | 30 min | Sweep tags/mentions/story shares → mark `posted`, check disclosure, log post URLs + code redemptions; flag high performers for §6 |

### Cost model (steady state: 10 boxes shipped/week)

Assume blended box mix (mostly T1, some T2, occasional T3):

| Line | Value |
|------|-------|
| Blended all-in cost per seeded box (COGS + packaging + ship) | **~$40–55** |
| Weekly seeding spend (10 boxes) | ~$400–550 |
| Expected post rate (industry norm for no-obligation gifting) | **20–40%** → 2–4 posts per 10 boxes |
| **Cost per posted content** | **$100–275** at the blended box cost (best case ~$100 at 40% post rate / $40 box; worst ~$275 at 20% / $55 box) |

Benchmarks: even the worst case beats typical paid micro-influencer post rates ($150–500+) — and we also get product-on-real-people proof, code-attributed revenue, and a warm relationship.

**Kill/scale rules:**
- Post rate <15% after 40+ boxes → tighten fit criteria and personalisation before scaling spend.
- Post rate >35% and code redemptions appearing → scale to 15–20 boxes/week.
- Track cost-per-attributed-order once codes redeem; any creator driving ≥3 orders is an automatic §6 candidate.

---

## 6. Re-engagement play — when a creator's content performs

Trigger: post materially outperforms (saves/shares above their norm, comments asking "where from," or ≥2 code redemptions within 30 days).

**Step 1 — within 48h of spotting it:** genuine founder reply/DM praising something specific in the content. No ask yet.

**Step 2 — the offer (3–7 days later), two levers, in order:**

1. **Paid usage rights.** Ask, never grab: "Your [reel/post] is exactly how we'd want the brand seen. Could we license it for [paid social / site / email] for [90 days / 12 months]? We pay for that — typical range $150–600 by scope for this tier; whitelisting/Spark Ads priced separately." Simple 1-page license, defined scope + term, prompt payment. Never perpetual-everything on a first deal.
2. **Affiliate upgrade.** Move them from courtesy code to real commission: 10–15% of net revenue on their code/URL (payable via affiliate tool or monthly manual payout), early access to new drops, a second gifted piece each season, first call for paid campaigns. Their audience-facing mechanic **stays the founding-customer gift-with-purchase — still never a % discount.**

**Step 3 — log it.** Tracker notes: date, offer, terms, response. These creators are the seed of the long-term ambassador roster; review the list monthly.

**Never:** retroactively claim rights because we gifted the product; run their content in ads without a signed license; convert the relationship into script-driven briefs. The voice that performed is the voice we're paying for.
