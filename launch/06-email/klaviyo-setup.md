# [BRAND] — Klaviyo Setup Checklist (Launch)

Working order: do sections 1–4 at least 3–4 weeks before launch (warmup needs the runway), 5–7 before the first flow goes live.

---

## 1. Klaviyo ↔ Shopify integration

- [ ] Install the Klaviyo app from the Shopify App Store; connect with a store-owner account.
- [ ] In Klaviyo → Integrations → Shopify: enable sync for **customers, orders, products, and catalog** (catalog powers dynamic product blocks in the cart/browse flows).
- [ ] Enable "Sync Shopify email subscribers to Klaviyo" and map to a single master list (e.g. `Newsletter`); keep the waitlist as its own list (`Waitlist`).
- [ ] Turn ON "Collect email subscribers at checkout" mapping — but confirm consent state maps as *subscribed only when the box is ticked* (required for UK/EU customers under GDPR/PECR).
- [ ] Verify key metrics are flowing in Klaviyo → Analytics → Metrics: **Placed Order, Started Checkout, Ordered Product, Fulfilled Order, Refunded Order, Checkout Started** (Shopify source), plus **Active on Site** and **Viewed Product** (Klaviyo source) after step 2.
- [ ] Place a test order end-to-end and confirm it appears on the test profile within minutes.
- [ ] Disable Shopify's own native abandoned-checkout email (Shopify Admin → Settings → Notifications) so it doesn't double-send against the Klaviyo flow.

## 2. Onsite tracking

- [ ] Confirm `klaviyo.js` is injected by the Shopify integration (view page source; look for the Klaviyo script with your 6-character public API key).
- [ ] Add the **Viewed Product** tracking snippet to the product template (`main-product.liquid` or theme equivalent) per Klaviyo's Shopify guide — this powers the browse-abandonment flow. (Some themes/integration versions inject it automatically — verify before adding, to avoid double-firing.)
- [ ] Test as an *identified* browser (click through from any Klaviyo test email first, so cookies are set), view a product, and confirm **Active on Site** and **Viewed Product** events land on your profile.
- [ ] Add signup forms: waitlist form (pre-launch, full-page or embedded) and a standard footer/popup form (post-launch). Set both to add to the correct list and to fire the form-submit event for ad-platform tracking.
- [ ] Confirm cookie-consent banner gates Klaviyo tracking appropriately for EU/UK visitors (onsite tracking should respect consent; check your consent-platform integration).

## 3. Flow triggers + filters (skip recent purchasers)

Build the four flows from `klaviyo-flows.md` with these settings:

| Flow | Trigger | Filters |
|---|---|---|
| Welcome/Waitlist | Subscribed to List `Waitlist` | Has Placed Order zero times since starting this flow (flow filter → auto-exit on purchase) |
| Abandoned Cart | Started Checkout | Has not Placed Order since starting this flow; has not Started Checkout again since starting this flow |
| Browse Abandonment | Viewed Product | Has not Placed Order since starting this flow; has not Started Checkout since starting this flow; has not been in this flow in the last 14 days |
| Post-Purchase | Placed Order | None on entry; PP3 uses a trigger split / wait-until on the Delivered/Fulfilled event |

- [ ] **Skip recent purchasers everywhere it matters:** on Welcome, Cart, and Browse flows add the profile/flow filter "Placed Order zero times since starting this flow" AND, for Browse, "Placed Order zero times in the last 30 days" so owners aren't marketed the piece they just bought.
- [ ] Turn **Smart Sending ON** for Cart and Browse flows (suppresses a send if the profile got any email in the last 16h — tune to 24h); turn it **OFF** for Post-Purchase (transactional-style updates must always send) and for the launch-day early-access email.
- [ ] Set flow-level exits: exit Cart flow on Placed Order; exit Browse flow on Started Checkout (the Cart flow takes over).
- [ ] Queue logic for launch week: schedule Welcome email W4 relative to [LAUNCH DATE]; if the date is set after subscribers join, send W4 as a one-off campaign to the `Waitlist` list instead of inside the flow.
- [ ] Test each flow with a seed profile before setting emails from Draft → Live. Go live in this order: Post-Purchase → Cart → Browse → Welcome.

## 4. Sending-domain warmup basics

- [ ] Set up a **dedicated sending (branded) domain**, e.g. `email.[branddomain].com` — Klaviyo → Settings → Email → Sending domains. Add the CNAME/DKIM records Klaviyo provides at your DNS host.
- [ ] Verify **SPF and DKIM** pass (Klaviyo shows status; confirm with a test send to a Gmail account → "show original").
- [ ] Publish a **DMARC** record on the root domain (start at `p=none; rua=mailto:...` to monitor, tighten later). Required by Gmail/Yahoo bulk-sender rules, along with one-click unsubscribe (Klaviyo handles list-unsubscribe headers automatically).
- [ ] **Warm the domain gradually** — new domains have no reputation. Weeks 1–2: send only to the most engaged segment (openers/clickers, recent signups). Roughly double volume every few sends (e.g. 500 → 1,000 → 2,500 → 5,000...) rather than blasting the full list on day one. The pre-launch waitlist drip is the ideal warmup traffic.
- [ ] Keep early sends to **engaged segments only** (engaged = opened/clicked in last 30–60 days, or subscribed in last 30 days) until bounce rate is stably <1% and spam-complaint rate <0.1% (target <0.05%).
- [ ] Set the friendly sender to `[FOUNDER NAME] at [BRAND]` for founder-voiced emails and `[BRAND]` for the rest; reply-to must be a monitored inbox ([SUPPORT EMAIL]) — the flows invite replies on purpose.

## 5. Double opt-in / list hygiene

- [ ] Turn **double opt-in ON** for the `Waitlist` and `Newsletter` lists (Klaviyo → Lists → Settings). Non-negotiable for UK/EU signups; also keeps bots and typos off the list, protecting warmup.
- [ ] Customise the confirmation email + confirmation page to brand voice (default Klaviyo copy is off-tone; keep it two sentences, warm, zero hype).
- [ ] Welcome flow trigger fires on list join, which with double opt-in means *after* confirmation — verify this in a test signup.
- [ ] Create a **sunset segment**: no opens/clicks in 120 days AND no orders in 180 days → send one "should we stop writing?" note (on-brand, no incentives) → suppress non-responders.
- [ ] Suppress hard bounces automatically (Klaviyo default) and review the suppression list monthly — never delete it.
- [ ] Never import purchased/scraped lists; only import prior consented lists with source + timestamp evidence.
- [ ] Footer compliance on every template: physical mailing address, unsubscribe link, brand name (CAN-SPAM, GDPR/PECR).

## 6. UTM conventions

Enable auto-UTM tracking in Klaviyo (Settings → Email → UTM tracking) with these conventions, so Shopify/GA4 attribution stays clean:

| Parameter | Convention | Example |
|---|---|---|
| `utm_source` | always `klaviyo` | `klaviyo` |
| `utm_medium` | `email` (flows and campaigns), `sms` if added later | `email` |
| `utm_campaign` | `{flow-or-campaign}_{email}` — lowercase, hyphens within names, underscores between parts | `welcome_w2-honest-math`, `cart_ac1-4h`, `launch_early-access` |
| `utm_content` | link position/variant | `cta-button`, `secondary-link`, `subj-a` |

- [ ] Naming rule for flows/campaigns inside Klaviyo mirrors `utm_campaign` (e.g. flow email name `AC1 — 4h reminder | cart_ac1-4h`) so reports read the same in Klaviyo, GA4, and Shopify.
- [ ] Document the convention in this file's repo and never hand-type UTMs in email bodies — let Klaviyo auto-append, and only override on special links (e.g. size-guide links get `utm_content=size-guide`).

## 7. Four dashboards to review weekly

Build these as saved Klaviyo dashboards/reports; review every Monday, same order:

1. **Deliverability health** — delivered rate, open rate by domain (Gmail vs Outlook vs Yahoo), bounce rate (<1%), spam-complaint rate (<0.05%), unsubscribe rate, by send. Watch for a single-domain open-rate drop = reputation problem at that mailbox provider. Critical during warmup.
2. **Flow performance** — per flow, per email: recipients, open, click, placed-order rate, revenue per recipient. Watch Cart AC1→AC3 conversion decay and Welcome W1→W4 drop-off; a weak email in the middle is a copy problem, a weak flow entry is a trigger/volume problem.
3. **List growth + acquisition quality** — new subscribers by form/source, double opt-in confirmation rate (target >70%; below that, fix the confirmation email), waitlist size vs launch goal, churn (unsubs + sunset suppressions) vs growth.
4. **Revenue attribution** — Klaviyo-attributed revenue vs total Shopify revenue (healthy DTC email programs run ~20–35% once flows mature), flow vs campaign split, revenue per email sent, and cross-check against Shopify's own UTM-based attribution monthly so nobody double-counts.

---

## Pre-launch smoke test (the last hour before go-live)

- [ ] One test signup → double opt-in confirm → W1 arrives with correct name fallback and perk copy.
- [ ] One test checkout abandon → AC1 at 4h with correct dynamic product block, no strikethrough pricing anywhere in the template.
- [ ] One test order → PP1 arrives alongside (not instead of) the Shopify transactional confirmation.
- [ ] Every rendered email re-checked against the copy QA checklist at the bottom of `klaviyo-flows.md` (lab-grown wording, zero discount language, materials line verbatim).
