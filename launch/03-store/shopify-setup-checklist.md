# Shopify Setup Checklist — Founder-Only Actions

These steps require the **store owner's** identity, legal-entity details, banking, or billing authority. No one else (and no agent) can complete them. Store: Shopify **Basic** plan, **USD** base currency. Work top to bottom; each item lists the exact click path.

Legend: `Settings` = the gear icon, bottom-left of Shopify admin.

---

## 1. Activate payments — Shopify Payments (and/or Stripe)

**Path:** `Settings → Payments → Activate Shopify Payments` (or "Complete account setup").

- [ ] Enter **legal business details**: registered entity name, business type, EIN (US) or company number, registered address. Must match your formation documents exactly — mismatches trigger payout holds.
- [ ] Provide **personal ID verification** for the owner/directors (passport/licence upload when prompted).
- [ ] Add the **business bank account** for payouts (account + routing / IBAN).
- [ ] Set **statement descriptor** to the brand name so card statements read [BRAND], not a mystery string (fewer chargebacks).
- [ ] `Settings → Payments → Shopify Payments → Manage`: review **payout schedule** and turn on **payout notifications**.
- [ ] Fraud: leave **automatic fraud analysis** on; for jewellery AOVs, plan to manually review any order flagged medium/high before crafting begins (you have a ~7-day production buffer — use it).
- If using **Stripe instead/additionally**: note Shopify charges **additional third-party transaction fees (2% on Basic)** when Shopify Payments is not used. Recommendation: Shopify Payments as primary; only add a third-party provider if Shopify Payments is unavailable for your entity's country.

## 2. Wallets — Shop Pay, Apple Pay, Google Pay

**Path:** `Settings → Payments → Shopify Payments → Manage → Wallets`.

- [ ] Toggle **Shop Pay** ON (accelerated checkout, materially lifts conversion).
- [ ] Toggle **Apple Pay** ON. Note: Apple Pay requires your domain to be live on the store (step 5) — re-check this toggle after connecting the domain.
- [ ] Toggle **Google Pay** ON.
- [ ] Optional (US): **Shop Pay Installments** — decide deliberately. Instalments fit jewellery AOVs, but review fees and the brand feel before enabling. This is a business decision only you can sign off.
- [ ] `Settings → Payments`: also enable **PayPal Express** if you have/want a PayPal business account (email verification is founder-only).

## 3. Shopify Markets — USD / GBP / EUR

**Path:** `Settings → Markets`.

- [ ] Confirm **primary market: United States (USD)**.
- [ ] `Add market` → **United Kingdom** → currency **GBP**.
- [ ] `Add market` → **European Union** (add the EU countries you'll ship to) → currency **EUR**.
- [ ] In each market → `Currency and pricing`: enable local currency, and set **price rounding** (recommended: round to `.00` — clean whole prices suit a never-discount, fair-value brand; e.g., $128 / £102 / €118).
- [ ] Consider setting **manual fixed prices per market** (rather than auto-converted, drifting FX prices) once GBP/EUR price lists are finalised — stable prices reinforce the fair-value promise. On Basic, per-market price adjustment is a percentage; fixed per-market price lists may require a plan/feature review — check current plan entitlements in the Markets settings screen.
- [ ] Note: currency conversion adds a **fee (~1.5%)** on converted orders via Shopify Payments — factor into GBP/EUR pricing.
- [ ] Test checkout in each currency (use a 100% preview or a $1 test product, then cancel/refund).

## 4. Taxes & duties

**Path:** `Settings → Taxes and duties`.

**US sales tax**

- [ ] You have **nexus** at minimum in your home state (physical nexus). Register with that state's revenue department, then in Shopify: `Taxes and duties → United States → Collect sales tax` and add the state + registration ID.
- [ ] Calendar a quarterly check of **economic nexus** thresholds (commonly $100k sales or 200 transactions per state) as revenue grows; add states as you cross thresholds.

**UK VAT**

- [ ] Rule of thumb: for consignments **≤ £135**, the seller must register for UK VAT and collect it at checkout; **above £135**, import VAT and duty are due at the border. Jewellery at your price points will straddle this line — decide with your accountant whether to register for UK VAT now (cleaner customer experience) or ship all UK orders DDP with the carrier billing you.
- [ ] If registering: HMRC VAT registration is founder-only (Government Gateway); then enter the VAT number under `Taxes and duties → United Kingdom`.

**EU VAT**

- [ ] IOSS covers only consignments **≤ €150** — many of your pieces will exceed it. For a consistent promise, recommend **DDP for all EU orders**.
- [ ] If you expect meaningful volume ≤ €150, discuss IOSS registration (via an EU intermediary) with your accountant; enter the IOSS number in `Taxes and duties`.

**Duties / DDP — the jewellery-specific recommendation**

- [ ] Customers hate surprise customs fees on premium purchases; the Shipping Policy already promises **DDP (duties & taxes included at checkout)** for UK/EU. Make checkout match:
  - `Settings → Taxes and duties → Collect duties and import taxes at checkout`. **On Basic this feature is a paid add-on / may require a plan upgrade (Advanced) — the settings screen shows your current entitlement and per-order fee.** Decide: enable the add-on, upgrade, or (fallback) ship DDP via your courier account (DHL/UPS "duties billed to shipper") and bake the cost into UK/EU market prices.
  - Whichever route: **do not launch UK/EU checkout until the DDP promise in the Shipping Policy is true.**
- [ ] Ensure correct **HS codes** on all products (7113.11 sterling-silver-based jewellery family — confirm with your customs broker) under each product's shipping section — needed for accurate duty calculation.

## 5. Domain

**Path:** `Settings → Domains`.

- [ ] `Connect existing domain` (enter the domain, then set the **A record → 23.227.38.65** and **CNAME www → shops.myshopify.com** at your registrar — registrar login is founder-only), or `Buy new domain` once [BRAND] is finalised.
- [ ] Set the custom domain as **primary**; enable redirect of all traffic to primary.
- [ ] Wait for the **SSL certificate** to issue (up to 48h); verify the padlock.
- [ ] Re-check the **Apple Pay** toggle (step 2) after the domain is live.
- [ ] Set up brand email on the domain (hello@[BRAND].com) and connect it under `Settings → Notifications → Sender email`, then authenticate (SPF/DKIM prompts in Shopify) so order emails don't land in spam.

## 6. Checkout branding

**Path:** `Settings → Checkout → Customize` (opens the checkout & accounts editor).

- [ ] Upload **logo**, set brand **colours** and **typography** so checkout doesn't feel generic.
- [ ] `Settings → Customer accounts`: choose account mode (recommend the modern customer accounts with passwordless login).
- [ ] `Settings → Checkout`: require **phone number** at checkout (courier contact for insured express delivery), set Tipping OFF, and set marketing consent checkboxes to opt-in (required posture for UK/EU).
- [ ] Add the policies (Shipping, Returns) under `Settings → Policies` — paste from `shopify-payloads.json` — so they auto-link in the checkout footer. Founder should be the one to click **Save** after legal review.

## 7. Password page — stay dark until launch

**Path:** `Online Store → Preferences → Password protection`.

- [ ] Keep **"Restrict access to visitors with the password"** CHECKED until launch day.
- [ ] Set the password-page message to a single teaser line + email capture (works even behind password).
- [ ] Launch-day flow (founder-only, in order): final pre-publish compliance checklist passes → payments live (step 1) → DDP verified (step 4) → domain primary + SSL (step 5) → **uncheck password protection → Save**.

---

### Also founder-only (quick hits)

- [ ] `Settings → Plan`: confirm Basic billing card; note upgrade decision point from step 4 (duties at checkout).
- [ ] `Settings → Users and permissions`: invite staff/agency with **least-privilege** roles; never share the owner login.
- [ ] `Settings → General`: legal business name & address (appears on invoices/policies).
- [ ] Turn on **two-step authentication** for the owner account (`Manage account → Security`).
