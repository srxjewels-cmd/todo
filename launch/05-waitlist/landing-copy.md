# [BRAND] — Waitlist Landing Page Copy

Launch deliverable · 2026-07-08
Compliance note: "lab-grown" must immediately precede "diamond" in every use, everywhere (page, meta, ads, email). All options below follow this rule — keep it when editing.
Materials wording (exact, do not paraphrase): **"18k gold vermeil over sterling silver, 2.5 microns+"**.

---

## 1. Headline options

Pick one for the hero. Each is built directly on the positioning ("real materials, made to order, fine-jewellery quality at demi-fine prices").

1. **Real 18k gold vermeil. Real IGI-certified lab-grown diamonds. Made to order.**
   *(Currently on the page — the positioning stated plainly. Strongest proof density.)*
2. **Fine-jewellery quality. Demi-fine prices. Nothing in between.**
   *(The value equation as a manifesto; lean on the proof points to carry the materials story.)*
3. **Real gold. Real IGI-certified lab-grown diamonds. Really made for you.**
   *(Warmer, rhythmic; "made for you" humanises made-to-order.)*
4. **Jewellery with nothing to hide.**
   *(Short, editorial, quiet-luxury restraint; requires the subhead to do the proof work.)*
5. **The end of choosing between real and reasonable.**
   *(Names the customer's actual dilemma; pairs well with subhead option B.)*

## 2. Subhead options

A. Fine-jewellery quality at demi-fine prices — no shortcuts on materials, no inflated markups. [BRAND] launches soon, and the waitlist comes first.
B. 18k gold vermeil over sterling silver, 2.5 microns+, set with IGI-certified lab-grown diamonds — each piece made to order and shipped in about 7 days.
C. Every piece is made when you order it: real 18k gold vermeil, real IGI-certified lab-grown diamonds, and a real certificate to prove it.
D. Quietly made, honestly priced. Join the waitlist for first access to the debut collection.

Pairing guidance: proof-heavy headline (1, 3) → lighter subhead (A or D); editorial headline (2, 4, 5) → proof-heavy subhead (B or C).

## 3. Perk framing rationale — access + gift, never % off

**The perk (exact wording):**
> Founding 100: first access to the debut collection + complimentary [BRAND] travel case + IGI certificate presented in a keepsake folio

**Why access + gift, and never a percentage:**

- **Discounts contradict the fair-value narrative.** The brand's core claim is that the price already *is* the fair price — real materials, made to order, no inflated markup to slash later. A "10% off" welcome offer tells the customer the list price was padded, and undoes the positioning in one line.
- **Discounts anchor; gifts elevate.** A % off trains customers to wait for the next code and permanently lowers the reference price. A gift (travel case, keepsake folio) adds perceived value on top of the full price and reinforces the fine-jewellery ritual of presentation.
- **Scarcity of access, not of margin.** "Founding 100" makes the reward earliness and belonging — first to see, first to own, a named cohort — which is the currency of quiet luxury. It costs a fixed, small COGS per member instead of an open-ended margin giveaway.
- **The gift is on-message.** The travel case says the jewellery is worth protecting; the IGI certificate in a keepsake folio restates the proof point (certified lab-grown diamonds) as an object you keep. Every element of the perk re-sells the positioning.
- **House rule for all future campaigns:** if a promotion can be written as "% off" or "$ off", rewrite it as access (early, exclusive, named) or gift (physical, on-brand, presented well). No exceptions — including Black Friday.

## 4. Meta title & description

**Meta title** (~66 chars):
`[BRAND] — IGI-Certified Lab-Grown Diamonds & 18k Gold Vermeil, Made to Order`
*(Trim to "[BRAND] — IGI-Certified Lab-Grown Diamonds, Made to Order" if the final brand name is long; keep under ~60 characters where possible.)*

**Meta description** (~180 chars — trim toward 155 once [BRAND] is set):
`Real 18k gold vermeil over sterling silver, 2.5 microns+. Real IGI-certified lab-grown diamonds. Made to order — fine-jewellery quality at demi-fine prices. Join the waitlist.`

**OG title / description** (already in the HTML):
- `[BRAND] — Coming Soon`
- `Real 18k gold vermeil and real IGI-certified lab-grown diamonds, made to order. Fine-jewellery quality at demi-fine prices. Join the waitlist for first access.`

## 5. Klaviyo wiring guide (3 steps)

1. **Create the "Waitlist" list.**
   In Klaviyo: *Audience → Lists & Segments → Create List* → name it exactly **Waitlist**. Add two custom profile properties now so Founding-100 tracking is automatic later: `waitlist_source` (e.g. "coming-soon-page") and rely on Klaviyo's built-in list-join timestamp to rank the first 100 sign-ups.

2. **Build and embed the sign-up form.**
   *Sign-up Forms → Create Form → Embed* (not popup — the page owns the layout), connect it to the **Waitlist** list, and style it to match the page (ivory background `#F7F2E9`, near-black button `#17140F`, no border radius). Publish, copy the snippet, and paste it into `landing-page.html` where the comment block `KLAVIYO EMBED FORM — PASTE SNIPPET DIRECTLY BELOW THIS COMMENT` marks the spot. If Klaviyo supplies a `klaviyo.js` script tag, paste it at the marked spot just before `</body>`. Then delete the fallback `<form>` between the `FALLBACK FORM` markers.

3. **Turn on double opt-in (recommended).**
   *List settings → Consent → Double opt-in.* For a pre-launch list mailed months from sign-up, double opt-in protects deliverability (clean list, engaged domain reputation for the launch send) and gives GDPR-grade consent evidence for UK/EU subscribers. Customise the confirmation email and success page to brand voice ("You're on the list — one more click to confirm"), and keep the confirmation email free of any offer language: the Founding 100 perk is access + gift, and even here, never % off.

---

*Compliance checklist before publish: every instance of "diamond(s)" is immediately preceded by "lab-grown"; materials line reads exactly "18k gold vermeil over sterling silver, 2.5 microns+"; no discount language anywhere, including form success states and confirmation emails.*
