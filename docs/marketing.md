# Marketing kit: the estimate, the follow-up and the ads

Working text for PL Development Inc. Everything here is a draft to edit in
your own voice. Names, prices and dates in the examples are placeholders.
The app's own copy (estimate page, proposal, roof check, card) already uses
these words; keep the same names everywhere:

| What the customer meets | Call it |
|---|---|
| The free result on the website | the estimate ("an estimate, not a quotation") |
| The appointment at the house | the roof visit |
| What they get after the visit (card and PDF) | your roof check |
| The sit-down over the bill and appliances | the energy audit |
| The priced document | your proposal |
| The company's net metering credit | credit on your bill |

## The funnel, step by step

1. **Estimate** on pldevinc.com (four questions, one minute). Link every
   ad, post and reply to it with a tag: `pldevinc.com/estimate?utm_source=fb&utm_medium=ad&utm_campaign=<name>`.
2. **Booking** on the same page. The thank-you says who will message and
   when; the lead appears on the job list with the figures the visitor saw.
3. **Roof visit** within the week, about an hour, free. Bring the test
   panel and meters; send the roof check card the same evening.
4. **Energy audit**: on the same visit when the house is small (ask for the
   bill photo and the appliance list when booking), or a second visit.
5. **Proposal** within two working days of the audit, valid 15 days.
6. **Signing** on Messenger (signed photo plus downpayment) or on a visit.

Measure five numbers every week, from the job list header: estimates run,
leads, visits, proposals, signed. Healthy targets to start: leads at 15 to
25% of estimates, visits at over 60% of leads, signed at 30 to 40% of
proposals.

## Messenger templates

Replace the parts in brackets. Short messages, one question each.

**Day 0, right after a booking (the owner, not a bot):**
> Hi [Name], this is [Owner] from PL Development. Thank you for booking a
> free roof visit. Which day this week suits you, morning or afternoon? The
> visit takes about an hour; we bring a test panel and meters so the
> proposal is exact. A photo of your latest bill helps us prepare.

**Day 1, no reply:**
> Hi [Name], just checking you saw my message. Would [day] or [day] work
> for the roof visit? No cost, no obligation.

**Day 3, still no reply (last nudge):**
> Hi [Name], I'll leave it here so I'm not a bother. Whenever you're ready,
> reply with a day and we'll come measure your roof. Your estimate was
> [N] panels at about ₱[price]; the visit settles the exact figure.

**Evening after the roof visit (with the card):**
> Here is your roof check, [Name]. Your roof holds [N] panels; you need
> about [n] to cover your bill. Next step is the energy audit on [date,
> time]; please have your latest bill ready.

**Sending the proposal:**
> Your proposal is attached, [Name]. In short: ₱[price] installed, your
> bill from ₱[before] to about ₱[after] a month, pays for itself in
> [years] years. Page 3 answers the usual questions (brownouts, net
> metering, warranties). It's valid until [date]. Happy to go through it on
> a call.

**Day 7 of the proposal (answer the two likeliest objections before they
are asked):**
> Two things people ask us, [Name]: in a brownout the battery takes over
> the moment the grid drops; and we file all the net metering papers with
> [electric company], you just sign two forms. Any question I can answer?

**Day 13 (two days before it lapses):**
> Hi [Name], your proposal is valid until [date]. If you'd like us to hold
> the price past that, a ₱10,000 reservation (deducted from the
> downpayment) keeps it for 30 days. Otherwise, no worries, we can re-quote
> later.

**After signing, at each milestone (the dates are on the proposal's
schedule):**
> Permit approved today. Materials pickup on [date], installation on
> [date] from about [time]. We'll need access to the roof and the panel
> board.
> Switched on and tested this afternoon. Net metering inspection and the
> two-way meter are expected around [date]; until then the system already
> cuts your daytime bill.

## Facebook ad angles

Three angles, one audience each. Use real photos of your own installs with
the town name; no stock images.

1. **Brownout (Batangas and Laguna lived it).** Hybrid buyers, ₱4,000 to
   ₱10,000 bills.
   > Lights on, aircon running, when the whole street is dark. Solar with a
   > battery, sized to your bill, priced from your exact roof. Free
   > one-minute estimate.
   Image: a lit house at night on a dark street.

2. **Bill swap (net metering, strongest numbers).** ₱5,000 to ₱10,000
   bills, no battery.
   > A ₱5,000 bill becomes about ₱1,100. The system pays for itself in
   > under 4 years, then runs for 20 more. See your own number in one
   > minute, free.
   Image: a bill with the before and after circled.

3. **Measured roof (why us).** Word-of-mouth lookalikes.
   > Other installers quote from a satellite photo. We put a test panel
   > and meters on your roof in Pila, Calauan, Tanauan or Lipa, free, and
   > quote exactly. Start with the one-minute estimate.
   Image: the installer on a roof with the meter in hand.

Landing-page headline options for the estimate page (the page's own
heading is "How much solar does your house need?"):

- "See what solar would do to your bill. Four questions, one minute, free."
- "Your ₱4,000 bill, down to a few hundred. Find out in a minute."

## Offer notes

- **The free visit needs a reason.** Say why it is free: most installers
  quote from a satellite photo; we measure the roof so the proposal is
  exact. That turns the visit into the product, not a sales call.
- **Carry the number forward.** Quick estimate ₱271,000 → measured
  proposal ₱266,900, or higher when the audit finds a planned aircon. A
  price that moves after measurement is a trust event when the reason is
  on paper; never promise that it goes down.
- **Battery as an add-on.** The estimate page already shows "add a battery
  for brownouts: +₱X". Keep that framing in conversation: the battery is
  insurance, not savings.
- **Reservation deposit.** ₱10,000, deducted from the downpayment, holds
  the price 30 days past the 15-day validity. Low risk, converts "thinking
  about it".
- **Financing.** Not offered yet; it will be its own module. Until then, no
  "from ₱X a month" line anywhere. The safe frame is "pay the price of
  about 45 months of your bill, then about 20 years of near-free power."
- **Trust devices to fill in under Settings.** Phone, Messenger link,
  Facebook page, owner's name, the PEE's name and PRC number, warranties,
  brands, where you install, where to pay. The estimate page and the
  documents print what is filled in.

## Where the estimate lives

**Now, before the website exists:** the estimate page is the website.
Point `pldevinc.com` at the app's tunnel and set
`SOLARAPP_PUBLIC_HOST=pldevinc.com` in the server's `.env`: that hostname
serves the estimate at its root and refuses everything else (the login,
the API and the documents stay on `solar.pldevinc.com`). Ads, posts and
the card's QR code then point at `https://pldevinc.com`. The README has
the tunnel steps.

**Later, with a real website:** embed the widget on a page such as
pldevinc.com/estimate with

```html
<div id="pld-solar-estimate"></div>
<script src="https://solar.pldevinc.com/widget/quick.js" defer></script>
```

and `SOLARAPP_PUBLIC_ORIGINS=https://pldevinc.com,https://www.pldevinc.com`
in the server's `.env`. Put the trust strip (owner, PEE, installs count,
three real roofs) and the privacy notice on the website page around it.
