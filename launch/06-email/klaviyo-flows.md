# [BRAND] — Klaviyo Flow Copy (Launch)

Complete send-ready copy for all 12 flow emails: Welcome/Waitlist (4), Abandoned Cart (3), Browse Abandonment (2), Post-Purchase (3).

**House rules baked into every email below**
- "lab-grown" always immediately precedes "diamond" / "diamonds". Never the bare word.
- Zero discount language. No sales, no codes, no urgency-by-price. Value is argued with facts, never with markdowns.
- Materials wording, verbatim: "18k gold vermeil over sterling silver, 2.5 microns+".
- Certification wording: IGI finished-jewellery reports.
- Made to order; ships in about 7 days.
- Tone: warm, confident, quiet luxury. Short sentences. No exclamation marks. No emojis.
- Personalisation uses Klaviyo tags, e.g. `{{ first_name|default:'' }}`. Where the fallback is empty, the greeting line should read naturally without a name ("Hello,").
- Placeholders the founder must fill: `[BRAND]`, `[LAUNCH DATE]`, `[FOUNDER NAME]`, `[HERO PIECE NAME]`, `[SUPPORT EMAIL]`, `[IG HANDLE]`, price/cost figures in Email W2.

---

## FLOW 1 — WELCOME / WAITLIST (4 emails)

**Trigger:** Subscribed to List → "Waitlist" (post double opt-in confirmation).
**Flow filter:** Has *not* Placed Order since starting this flow (auto-exit on purchase).

---

### Email W1 — Instant welcome + founding perk confirmation
**Timing:** Immediately on signup.

**Subject:** You're in. Your founding place is confirmed.
**Preview text:** What founding status at [BRAND] actually means — and what happens next.

**Body:**

Hello {{ first_name|default:'' }},

Welcome to [BRAND]. You're now on the founding list — the small group who gets first access when we open.

Here's what that means, concretely:

- **First access.** You'll shop the launch collection 48 hours before anyone else. Every piece is made to order, so early access means an earlier place in the making queue.
- **A founding thank-you.** Your first order arrives with a complimentary care kit — polishing cloth and keep-it-beautiful instructions — and a handwritten note. *(Founder: confirm/adjust perk — must remain non-discount.)*
- **A say in what we make next.** Founding members vote on upcoming designs before they go into production.

And here's what we are, in one line: real 18k gold vermeil and real IGI-certified lab-grown diamonds, made to order — fine-jewellery quality at demi-fine prices.

No sales. No codes. Just honest pieces at honest prices, made when you order them.

Over the next few days we'll send you three short notes: how our pricing works, what a lab-grown diamond actually is, and exactly how launch week will run. That's it — we don't crowd inboxes.

Warmly,
[FOUNDER NAME]
Founder, [BRAND]

**CTA button:** See what's coming → [teaser/lookbook page]

---

### Email W2 — Brand story + fair-value "honest math"
**Timing:** 2 days after W1.

**Subject:** The honest math behind our prices
**Preview text:** Where every dollar goes when jewellery is made to order — no middlemen, no markdown games.

**Body:**

Hello {{ first_name|default:'' }},

Most jewellery pricing is designed so you never ask how it's built. We'd rather show you.

**How traditional fine jewellery is priced.** A piece typically passes from workshop to wholesaler to distributor to a retail floor with rent to cover. Each step takes its share. By the time it reaches the glass case, the price is commonly six to ten times what the piece cost to make. Then, twice a year, it goes "on sale" — which tells you what it was really worth all along.

**How [BRAND] is priced.** We design the piece, we have it made when you order it, and we ship it to you. One maker, one margin, no warehouse of unsold stock priced into your purchase. Here's the shape of it, using our [HERO PIECE NAME] as the example:

- Materials — sterling silver, 18k gold (2.5 microns+ of it), and an IGI-certified lab-grown diamond: [$X]
- Skilled making, setting, and finishing: [$Y]
- IGI finished-jewellery report, packaging, and delivery: [$Z]
- Our margin — the part that pays our small team and keeps us independent: [$M]
- **Your price: [$PRICE]** *(Founder: insert real figures; roughly 2–3x landed cost is the honest range.)*

That's the whole equation. Because the math is honest on day one, it never goes "on sale". The price you see is the fair price — today, at Christmas, always. We think that's what respect for a customer looks like.

Warmly,
[FOUNDER NAME]

**CTA button:** Read our fair-price promise → [pricing/values page]

---

### Email W3 — Lab-grown diamond education teaser
**Timing:** 2 days after W2.

**Subject:** A real lab-grown diamond, explained in two minutes
**Preview text:** Same carbon, same sparkle, same grading standards — and an IGI report to prove it.

**Body:**

Hello {{ first_name|default:'' }},

A quick note about the stones we set — because "lab-grown" gets used loosely, and we'd like to be precise.

**A lab-grown diamond is a real diamond-crystal of pure carbon.** Chemically, physically, and optically identical to a mined stone — the same hardness, the same fire, the same brilliance. The only difference is origin: grown above ground over weeks rather than mined from it. Not cubic zirconia, not moissanite, not a simulant of any kind.

**Graded to the same standard.** Every lab-grown diamond we set is assessed by IGI — the International Gemological Institute — against the same criteria used for mined stones: the 4Cs of cut, colour, clarity, and carat.

**Certified as finished jewellery.** Here's the part most brands skip: we don't hand you a loose-stone certificate for a stone you'll never see outside its setting. Every [BRAND] piece ships with an IGI finished-jewellery report — an independent document assessing the actual piece on your hand, stone and setting together.

And beneath every stone: 18k gold vermeil over sterling silver, 2.5 microns+. Real precious metal, all the way through — no brass, no mystery alloy.

Real stones, real gold, real paperwork. That's the whole idea.

Warmly,
[BRAND]

**CTA button:** Learn how our lab-grown diamonds are made → [education page]

---

### Email W4 — Launch-week early-access mechanics
**Timing:** 2–3 days before [LAUNCH DATE] (scheduled; move this email to a campaign if flow timing can't be pinned to the date).

**Subject:** Your early access opens [LAUNCH DATE]
**Preview text:** 48 hours before the public, and an earlier place in the making queue. Here's exactly how it works.

**Body:**

Hello {{ first_name|default:'' }},

It's nearly time. Here is exactly how launch week will work for founding members — no games, just logistics.

**1. Early access opens [LAUNCH DATE], [TIME] [TIMEZONE].** You'll receive an email with your private link. It works for 48 hours, then the collection opens to everyone.

**2. Why early matters here.** Every [BRAND] piece is made to order, and pieces are made in the order they're purchased. Early access isn't a price event — prices are identical before, during, and after launch, always. It's a queue event: order in your window and yours is on the bench first, shipping in about 7 days.

**3. What you'll find.** The full launch collection — 18k gold vermeil over sterling silver, 2.5 microns+, set with IGI-certified lab-grown diamonds. Each piece ships with its IGI finished-jewellery report.

**4. Your founding thank-you.** The complimentary care kit and a note from us, tucked into your first order.

One suggestion: if you already know your ring size, have it ready. If you don't, our size guide takes two minutes — link below — and doing it now means nothing slows you down on the day.

See you at the front of the line.

Warmly,
[FOUNDER NAME]

**CTA button:** Find your size before launch → [size guide]
**Secondary link:** Preview the collection → [lookbook]

---

## FLOW 2 — ABANDONED CART (3 emails)

**Trigger:** Started Checkout (fallback: Added to Cart if checkout event volume is low).
**Flow filters:** Has not Placed Order since starting this flow; has not Started Checkout again since starting this flow (restarts the flow). Smart Sending on.
**Angle throughout:** "Your piece hasn't been made yet — it's made for you." Never discounts; offer certainty and help instead.

---

### Email AC1 — 4-hour reminder
**Timing:** 4 hours after Started Checkout.

**Subject:** Your piece hasn't been made yet
**Preview text:** It's made for you — the bench is ready when you are.

**Body:**

Hello {{ first_name|default:'' }},

You left something at the bench.

{{ event.extra.line_items.0.product.title|default:'The piece you chose' }} isn't sitting in a warehouse waiting to be picked. At [BRAND], nothing is. Your piece hasn't been made yet — it's made for you, and making begins the moment you order.

[ DYNAMIC BLOCK: cart item image, name, price — no strikethroughs, ever ]

A quick recap of what you'd be starting:

- 18k gold vermeil over sterling silver, 2.5 microns+
- An IGI-certified lab-grown diamond, documented in a finished-jewellery report that ships with the piece
- Made to order for you, shipping in about 7 days

Your selections are saved. Whenever you're ready, the bench is too.

Warmly,
[BRAND]

**CTA button:** Return to your piece → [checkout link]

---

### Email AC2 — 24-hour IGI certificate / craftsmanship trust
**Timing:** 24 hours after Started Checkout (if no purchase).

**Subject:** The paperwork that comes with your piece
**Preview text:** An independent IGI finished-jewellery report — most demi-fine brands can't offer one. Here's why we do.

**Body:**

Hello {{ first_name|default:'' }},

Still thinking it over? Good — jewellery should be considered. Let us show you what you'd actually be getting.

**Independent proof, not brand promises.** Every [BRAND] piece ships with an IGI finished-jewellery report. IGI — the International Gemological Institute — is one of the world's most established gem laboratories, and the report covers your finished piece: the lab-grown diamond's grading and the setting it lives in. It isn't our opinion of our own work. It's theirs.

**Metal you can verify.** 18k gold vermeil over sterling silver, 2.5 microns+. "Vermeil" is a legally defined standard — a thick layer of real gold over solid sterling silver, not plating over brass. The "2.5 microns+" is the part that determines how it wears, which is why we put the number in writing.

**Made by hand, for you.** Because your piece is made when you order it, it's cast, set, polished, and inspected as a one-off — then checked against its report before it ships, about 7 days later.

[ DYNAMIC BLOCK: cart item ]

Your cart is saved. If anything is giving you pause, just reply to this email — a real person reads these and will answer honestly, including "no" when a piece isn't right for you.

Warmly,
[BRAND]

**CTA button:** Complete your order → [checkout link]
**Secondary link:** See a sample IGI report → [certificate explainer page]

---

### Email AC3 — 72-hour final nudge: FAQ objections, offer help
**Timing:** 72 hours after Started Checkout (if no purchase). Final email in flow.

**Subject:** Three questions people ask before ordering
**Preview text:** Sizing, how vermeil wears, and what the IGI report covers — answered straight, plus a human if you need one.

**Body:**

Hello {{ first_name|default:'' }},

This is the last note we'll send about the piece in your cart — we don't believe in chasing. But before it goes quiet, here are honest answers to the three questions people most often ask at exactly this point.

**"What if I get the size wrong?"**
Our size guide takes two minutes and works with a strip of paper or a ring you already own. And if the fit still isn't right when it arrives, we'll make it right — resizing or remaking per our fit promise. You won't be stuck with a wrong size. [Size guide →]

**"Will vermeil last?"**
Ours is 18k gold vermeil over sterling silver, 2.5 microns+ — roughly five times the legal minimum gold thickness for vermeil, over a solid precious-metal core. Worn with basic care (the kit we include covers it), it's built for years of regular wear, not a season. [Care guide →]

**"What exactly does the certificate cover?"**
An IGI finished-jewellery report is issued by the International Gemological Institute for your specific finished piece — the lab-grown diamond's grading and the piece it's set in. It ships in the box, in your name if you wish. [Certificate explainer →]

You may notice what's not in this email: a countdown, or a code. There never will be. Our prices are the honest price on day one, so there's nothing to mark down and no reason to rush you.

If something else is holding you back — a gift deadline, a metal allergy question, styling doubts — reply to this email or write to [SUPPORT EMAIL]. A real person will help, even if the honest answer is that this isn't your piece.

Whenever you're ready, we'll start making.

Warmly,
[FOUNDER NAME]

**CTA button:** Return to your piece → [checkout link]
**Secondary CTA:** Ask us anything → mailto:[SUPPORT EMAIL]

---

## FLOW 3 — BROWSE ABANDONMENT (2 emails)

**Trigger:** Viewed Product.
**Flow filters:** Has not Placed Order since starting this flow; has not Started Checkout since starting this flow (cart flow takes over if they did); has not been in this flow in the last 14 days (throttle). Smart Sending on.

---

### Email BA1 — 24-hour styling angle
**Timing:** 24 hours after Viewed Product.

**Subject:** Noticed you looking. Here's how we'd wear it.
**Preview text:** Three ways to style the {{ event.extra.product.title|default:'piece' }} you were eyeing — from desk to dinner.

**Body:**

Hello {{ first_name|default:'' }},

You spent a moment with the {{ event.extra.product.title|default:'piece' }}. It's one of our favourites to style, so — three ways we'd wear it:

[ DYNAMIC BLOCK: viewed product image, name, price ]

**On ordinary days.** This is the quiet-luxury trick: one certified piece worn with everything. The 18k gold vermeil over sterling silver, 2.5 microns+ is made for daily wear, so it can be the thing you simply never take off.

**Layered.** Pair it with the finer pieces you already own. Because the gold is real 18k, it sits naturally beside inherited and fine pieces — no colour mismatch, no odd-one-out.

**As the only jewellery you wear.** An IGI-certified lab-grown diamond doesn't need company. With a bare neckline or a rolled cuff, one real stone says more than a stack of plated ones.

[ DYNAMIC BLOCK: 2–3 "wears well with" recommendations ]

If it's still on your mind, that usually means something. And since every piece is made to order, whenever you choose it, it will be made for you — shipping in about 7 days.

Warmly,
[BRAND]

**CTA button:** Take another look → [product page]

---

### Email BA2 — 3-day education + social proof
**Timing:** 3 days after Viewed Product (if no checkout started). Final email in flow.

**Subject:** Why pieces like this usually cost far more
**Preview text:** Real 18k gold vermeil, a real IGI-certified lab-grown diamond, and what early customers are saying.

**Body:**

Hello {{ first_name|default:'' }},

A short one, because the piece you viewed deserves context.

Jewellery at our price point usually makes a quiet compromise: plated brass, or a simulated stone, or paperwork that amounts to the brand grading itself. Pieces without those compromises usually sit behind fine-jewellery glass at several times the price. [BRAND] exists in the gap:

- **Real metal.** 18k gold vermeil over sterling silver, 2.5 microns+ — precious metal through and through.
- **Real stones.** IGI-certified lab-grown diamonds — chemically and optically identical to mined stones, graded by the same 4Cs.
- **Real proof.** An IGI finished-jewellery report with every piece. Independent, in writing, in the box.
- **Real fairness.** Made to order in about 7 days, priced honestly from day one — never marked up to be marked down.

And because you shouldn't take our word for it:

> "[UGC/REVIEW QUOTE 1 — e.g., wore it daily for a month, looks like the day it arrived]" — [NAME], [CITY]

> "[UGC/REVIEW QUOTE 2 — e.g., the IGI report made it feel like real fine jewellery, because it is]" — [NAME], [CITY]

*(Founder: swap in two genuine, permissioned reviews; until launch reviews exist, use quotes from sampling/preview feedback and label them as such.)*

That's the case. No countdown attached — the piece will be the same fair price whenever you're ready, and it will be made for you the day you order.

Warmly,
[BRAND]

**CTA button:** See the piece again → [product page]
**Secondary link:** How our lab-grown diamonds are certified → [education page]

---

## FLOW 4 — POST-PURCHASE (3 emails)

**Trigger:** Placed Order.
**Flow filters:** None on entry (every buyer gets it). PP3 waits on the Delivered event (via Shopify fulfilment tracking) rather than a fixed delay.

---

### Email PP1 — Order confirmed + what made-to-order means + timeline
**Timing:** Immediately on Placed Order. (Supplements — does not replace — the transactional Shopify order confirmation.)

**Subject:** Confirmed — your piece goes to the bench
**Preview text:** What made-to-order means, and exactly what happens over the next 7 days.

**Body:**

Hello {{ first_name|default:'' }},

Thank you. Your order is confirmed — and something slightly unusual happens next: your piece gets *made*.

[ DYNAMIC BLOCK: order summary — items, order number ]

Nothing you ordered was sitting on a shelf. Made to order means your piece is cast, set, and finished for you, after you order it. It's how fine jewellery has always properly been done — it means no warehouses of unsold stock built into the price, and a piece that has only ever belonged to you.

**Your timeline:**

- **Today** — your order enters the making queue.
- **Days 1–5** — casting, setting your lab-grown diamond, polishing, finishing. We'll send a note from the bench mid-way.
- **Days 5–7** — final inspection, checked against its IGI finished-jewellery report, then packed with your certificate and care kit.
- **~Day 7** — your piece ships. Tracking lands in your inbox the moment it does.

If anything about your order needs changing — size, engraving, address — reply within 24 hours and we can usually catch it before casting. After that, your piece is quite literally in the works.

We're glad it's yours.

Warmly,
[FOUNDER NAME]
Founder, [BRAND]

**CTA button:** View your order → [order status page]

---

### Email PP2 — Production update + care guide + certificate explainer
**Timing:** 4 days after Placed Order (mid-production).

**Subject:** From the bench: your piece is taking shape
**Preview text:** A production update, how to care for 18k gold vermeil, and how to read your IGI report.

**Body:**

Hello {{ first_name|default:'' }},

A note from the bench: your piece is mid-way through making. The casting is done, your lab-grown diamond is being set, and finishing and inspection come next. You're on schedule to ship on time — around day 7.

While it's being finished, two things worth reading now:

**Caring for your piece.** Your jewellery is 18k gold vermeil over sterling silver, 2.5 microns+ — real precious metal that will reward small habits:

- Last on, first off: put jewellery on after lotions and perfume, remove before showering, swimming, and sleep.
- Wipe with the soft cloth from your care kit after wear.
- Store in the pouch it arrives in, away from other pieces.
That's genuinely all it takes for years of wear.

**Reading your IGI finished-jewellery report.** In your box you'll find a report from the International Gemological Institute — an independent laboratory, not us grading ourselves. It documents your finished piece: the lab-grown diamond's cut, colour, clarity, and carat, plus the setting and metal. Keep it with your important papers; it's your piece's provenance, useful for insurance and, someday, for whoever inherits it. Full explainer at the link below.

Next email you get from us will contain tracking.

Warmly,
[BRAND]

**CTA button:** How to read your IGI report → [certificate explainer page]
**Secondary link:** The full care guide → [care page]

---

### Email PP3 — Delivered + review/UGC ask (with FTC disclosure note)
**Timing:** 3 days after Delivered event (give her time to wear it).

**Subject:** How does it feel on?
**Preview text:** Two minutes of your honesty would mean a great deal — and here's how to tag us properly if you share it.

**Body:**

Hello {{ first_name|default:'' }},

Your piece has been with you a few days now — long enough for first impressions to become real ones. We hope it already feels like yours.

Two small asks, only if you're willing:

**Tell the truth about it.** A short review — two minutes — helps other women decide whether [BRAND] is for them. We publish reviews unedited, the less varnished the better; honest words are worth more to us than kind ones. [Leave a review →]

**Show us how you wear it.** If you share your piece, tag [IG HANDLE] — we feature customer photos (with your permission) far more often than our own, because how you style it is more interesting than how we do.

*A note on disclosure, because we're that kind of brand:* if you ever receive anything from us in exchange for a post — a gift, a feature, product to review — FTC and UK/EU advertising rules ask that you say so plainly in the post itself (for example "#gift" or "gifted by [BRAND]"). An ordinary customer post about a piece you bought needs no label. If we ask you for content in future, we'll always tell you exactly what disclosure applies.

If anything is less than right — fit, finish, anything — reply to this email before you review, and a real person will fix it.

Thank you for being one of the first.

Warmly,
[FOUNDER NAME]
Founder, [BRAND]

**CTA button:** Leave your review → [review link]
**Secondary CTA:** Tag us → [IG HANDLE]

---

## Copy QA checklist (run before any email goes live)

- [ ] Every "diamond"/"diamonds" is immediately preceded by "lab-grown".
- [ ] Zero discount vocabulary anywhere: no sale, % off, code, deal, save, markdown, "free" framed as price promotion.
- [ ] Materials line verbatim: "18k gold vermeil over sterling silver, 2.5 microns+".
- [ ] IGI always expanded once per email as "International Gemological Institute" where space allows; "finished-jewellery report" wording intact.
- [ ] All placeholders ([BRAND], [LAUNCH DATE], [$X] figures, review quotes, links) replaced.
- [ ] Footer on every email: physical mailing address + one-click unsubscribe (CAN-SPAM/GDPR).
