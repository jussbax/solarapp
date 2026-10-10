# Marketing and sales audit, round 5: the first real photos on the website

(The auditor's report, delivered to the coordinator as a message; evidence crops stayed in the session scratch folder.)

Audit only; nothing under the repository was changed and site/dist was not rebuilt. Lens: the owner's thirteen drone frames are the first proof on the site that PL Development has put panels on real roofs. The three chosen frames, the hero and the share image were judged the way a Laguna or Batangas homeowner comparing two installers on Messenger would, and the way a competitor's salesman looking for something to screenshot would.

Standing constraints respected: no town, size, brand or customer name the owner has not given (every caption below carries a slot and a question instead); no financing; no utility branding; "estimate", "roof check", "proposal".

## Method

- Read: the round-5 brief, the round-3 marketing report, DECISIONS.md "Product" and "Customer documents" (and "Brand", "The website and the public process", "The service area is the whole Philippines"), docs/marketing.md (Messenger templates, Facebook ad angles), `site/pages/*.html`, `site/layout.html`, `site/build.py`, `site/tools/photos.py`, `site/static/site.css` (photo rules).
- Looked at all thirteen originals (25–37), the six 960 px web versions and `og-home.jpg`, then zoomed into the details that drive the findings (the orange cable and the aircon brand on 25, the cable runs on 36, the yard clutter and the neighbour's laundry inside the published 36 crop, the sign and the people on 29–32, the shade on 35, panel counts on 26 and 37).
- The home page as served at 1280 and 390, to see how each card reads at its real size.
- Candidate crops for the fixes, so the coordinator could look before deciding.

## Verdict

The choice of 25 as hero and share image is right: finished, clean, mid-day light, a typical eight-panel home system filling the frame, a house a visitor can picture as their own. The three-card section is the right size for three sites, and the captions are written in the customer's words. The photo pipeline (exact 4:3 crops, two widths, WebP and JPEG, metadata dropped, placeholders stripped from the public build) is sound.

What costs sales or trust today, in order:

1. Two captions state things the frames contradict or do not show: "Panels on four faces" (the frame shows three faces with panels and the fourth empty) and "clamped to the framing through the sheet" (not visible, and on a rib-type roof not necessarily what was done). These are the lines a competitor screenshots.
2. The section lead claims "Every one measured on the roof first … Photographed from the air after switch-on" for three jobs the owner has not described; frame 36 itself shows a cable coil and a box in the yard.
3. No town and no size on any card: the section reads like a stock gallery; the owner's data turns it into proof.
4. Site B's loose cable runs and the yard clutter inside the published crop, and site C's palm shade, are the two frames a knowledgeable buyer will question; one re-crop and two owner answers settle them.
5. The same frame (25) appears twice on the home page, which reads as "one good photo".
6. The share image carries the customer's aircon unit with a legible third-party brand in the corner that Messenger's square preview makes prominent.

Nothing published is fabricated; the risk is in three sentences and two crops, all S effort.

## Findings, ranked by lost sales first

Severity: Critical (costs the sale or breaks trust), Major (a gap a buyer or a competitor will find), Minor (polish). Effort: S under an hour, M a day, L more. "Owner" means the fix waits on the owner's answer.

| # | Sev. | Eff. | Where | Finding |
|---|---|---|---|---|
| C1 | Critical | S | `site/pages/index.html` card 2 caption and alt | "Panels on four faces of one roof": the frame shows three faces with panels (6, 10, 4) and the fourth face empty |
| C2 | Critical | S | card 1 caption | "clamped to the framing through the sheet": not visible in the frame; on a rib-type roof the fixing may be rib clamps, and the owner has not said |
| C3 | Critical | S + owner | section lead | "Every one measured on the roof first, then designed to the bill. Photographed from the air after switch-on." claims a method and a moment for three jobs nobody has confirmed |
| M1 | Major | Owner | the three cards | No town, no size, no system kind on any card; the section cannot answer "saan 'yan, ilang kW?" |
| M2 | Major | S + owner | card 2 (`hip-roof-town-960.jpg`, from 36) | Loose cable runs across the roof surface between the three groups; the published crop also shows a cable coil and a box in the yard (bottom left) and the neighbour's laundry (top right) |
| M3 | Major | Owner | card 3 (`three-roofs-palms-960.jpg`, from 35) | The palms' shadow lies across five or six panels of the main array; the caption's process line is right but needs the hour and the design answer |
| M4 | Major | S | hero and card 1 | The same frame (25) is the hero and card 1 |
| M5 | Major | S | `og-home.jpg`; `site/layout.html` | Share crop runs to the bottom of 25 and carries the customer's aircon unit with a legible brand; one share image for every page; no `og:image:alt` |
| M6 | Major | S + owner | section lead | No line on whose installations and whose photos these are, nor that the homeowners agreed |
| m1 | Minor | S | card 1 alt | Alt text names "mango" trees; unverifiable |
| m2 | Minor | Owner | 25–28, hero and share image | A bright orange cable leaves the lower row at the left and runs to the roof edge |
| m3 | Minor | S | `site/static/photos/hip-roof-town-wide-*` | Frame 33 (neighbour's house and laundry, cables large) is served at a public URL though no page uses it |
| m4 | Minor | S | `layout.html` footer; `about.html` "Where we install" | Footer fallback "Installs in Laguna and Batangas" beside a hero that says "the whole Philippines"; About lists two provinces under a lead that says the whole country |
| m5 | Minor | S (UX) | hero on the phone | On a phone the hero photo sits below the four tick points: the first screen a Facebook visitor sees has no roof on it |
| m6 | Minor | S | section eyebrow | "Recent installations": nobody has said when these were done |

### Critical

**C1 The hip-roof caption counts four faces; the frame shows three. S**
In 36 (and 29–34) the panels sit on the left face (two columns of three), the back face (a row of six and a two-by-two) and the front face (a two-by-two); the right face carries nothing. Three groups, three faces, twenty panels; the alt text itself lists three groups. A buyer counts; a competitor posts the screenshot with "they can't count their own roof"; the PEE who reads it wonders what else is approximate. Fix, caption: "Twenty panels in three groups, each fitted to its own face of the roof. A roof with no single large face still carries a full system." Alt: "Twenty solar panels in three groups on a grey corrugated hip roof in a built-up street". Keep "twenty" only if the engineering auditor's count agrees (this count from 36: 6 + 10 + 4).

**C2 "Clamped to the framing through the sheet" is not in the frame and may not be true of this roof. S**
The frame (25–28) shows rails and end clamps, not what is under them. On a rib-type roof installers often use rib clamps that make no hole; the home page FAQ describes the firm's general method, which is allowed, but this caption attaches it to one job the owner has not described. If site A was done with rib clamps, the caption is wrong on the firm's own showcase; "through the sheet" is also the sentence that starts the leak conversation with a buyer's roofer. Fix: "Two rows of four, set in from the edges of the roof. A typical home system." Ask the owner how site A was fixed; if it was through the sheet to the purlins, the FAQ already says so and the caption does not need to.

**C3 The section lead claims a method and a moment for jobs nobody has confirmed. S + owner**
The owner sent frames with no towns, sizes or dates; the test-panel roof visit is the method the app was built for and may postdate these installs; frame 36 shows a coil of black cable and a box in the yard and cable runs still lying on the sheet, which looks like the day the drone went up, not a switched-on, handed-over job. This is the "we measure before we quote" promise, the site's whole positioning, bolted to three real houses; if one of those customers, or a competitor who knows the job, reads it and it is not so, every other claim on the page goes with it. Fix now: "Three of our installations, photographed from the air." After the owner confirms per site (visit with the test panel: yes/no; photographed after switch-on: yes/no): "Each one measured on the roof first, then designed to the bill, and photographed from the air after switch-on." Only with three yeses; with fewer, keep the plain line.

### Major

**M1 No town, no size, no system kind on any card. Owner**
The first two things a Filipino buyer asks when shown a photo are where it is and how big it is; docs/marketing.md's own ad rule is "real photos of your own installs with the town name"; a gallery without places reads as stock. This was the round-3 ask; the photos came, the data did not. The three headings and first sentences with slots:
- Card 1: "Eight panels on a rib-type roof, [town]" / "[kWp] kWp, [with a [kWh] kWh battery | on net metering]. Two rows of four, set in from the edges of the roof. A typical home system."
- Card 2: "A hip roof in a built-up street, [town]" / "Twenty panels, [kWp] kWp, [with a [kWh] kWh battery | on net metering], in three groups, each fitted to its own face of the roof. A roof with no single large face still carries a full system."
- Card 3: "Three roofs of one property, [town]" / "[N] panels, [kWp] kWp, across the main house, the annex and a smaller roof[, with a [kWh] kWh battery]. Shade like the palms' is what the roof visit measures, so the design counts it in."
Town only, never the barangay or the street; the system kind in the site's three names. What to ask the owner for each site: town; panel count and wattage (or kWp); battery or net metering, and the battery's kWh; month and year of switch-on; whether the roof visit with the test panel was done; the customer's go-ahead to show the roof (a Messenger "yes" is enough). Until the data arrives, the headings stay as they are.

**M2 Site B: cable runs on the roof surface, and installation leftovers inside the published crop. S + owner**
Black cables lie loose on the corrugated sheet from the left group across to the back group and from there down to the front group; at the bottom left of the published frame a coil of black cable and a box sit in the yard; at the top right the neighbour's yard with laundry and a yellow basin. On a phone the card is 660 px wide and all of it is legible. A buyer who has read anything, and every competitor's salesman, sees DC cable lying in the water path and the sun and asks "ganyan ba ang gagawin sa amin?"; the yard clutter says "not finished" under a lead that says "after switch-on"; the laundry is what a privacy-minded reader notices. Fix: (1) ask the owner whether the cables were clipped or put in conduit after the photo; if yes, ask for an "after" frame at the same angle and replace 36 with it; (2) either way, re-crop now so the yard and most of the neighbour's yard go: `python site/tools/photos.py 36.jpg --name hip-roof-town --crop 0,0.12,0.73,0.85` (the three groups stay whole, the empty right face and the yard go, the neighbour's yard shrinks to a corner); (3) never publish 33 or 34 at any size: the neighbour's whole house, balcony and washing fill the top third and the cables are larger. The engineering auditor should say whether surface-laid cable is acceptable work; the marketing call is only that the site should not invite the question until the owner has the answer.

**M3 Site C: the palms' shade lies across the main array. Owner**
The shadow covers five or six panels of the top row and part of the second (35; in 37 the same). The caption's process line is the right move (a process claim the site already makes, not a job claim), but it is a sentence a buyer who knows that shade on one panel pulls down a whole string will not accept without more. The competitor's easiest screenshot: "they put panels under coconut trees". Fix: ask the owner the hour the frame was shot (no EXIF survives; the long shadows say early or late) and whether the design accounted for the palms (string layout, optimisers, trimming agreed with the customer). With the answers: "[N] panels across the main house, the annex and a smaller roof. The palms throw this shade only [early in the morning | late in the afternoon]; the roof visit measured it and the strings are laid out around it." Without them, keep the frame and the safer line, which claims only the process: "Shade like the palms' is what the roof visit measures, so the design counts it in." Do not swap in 37 to hide it; the shade is there too, and a top-down frame of a big array reads colder than 35.

**M4 The same frame twice on one page. S**
Hero and card 1 both use `rib-roof-eight` (25). A visitor who scrolls sees the hero again three screens later and concludes there is one good photo. Fix: card 1 → `rib-roof-eight-angle` (27, already built, unused): alt "Eight solar panels on a rib-type metal roof seen from the side, with the trees beside the house"; heading unchanged. 25 stays the hero and the share image.

**M5 The share image: right frame, wrong crop; one image for every page. S**
The array is centred, which is right for Messenger and Facebook; but the crop keeps the customer's aircon unit at the lower left with a legible brand name, and in the square preview Messenger shows on phones it sits in the corner of the only share image. Every Messenger reply with a link, every Facebook post, carries this frame; a third-party brand on it is sloppy and the unit draws the eye from the panels. Fix: `python site/tools/photos.py 25.jpg --og --crop 0,0.12,1,0.82` (the array centred, trees and field above, no aircon). Add `og:image:alt`. Per page: let `build.py` read an optional `<!-- og_image: ... -->` meta with `og-home.jpg` as the default; today every page can share 25 (it is the product), and when the owner photographs an inverter and battery on a wall, `brownouts.html` shares that, and `about.html` shares the owner on a roof.

**M6 Whose installations, whose photos, and did the customers agree. S + owner**
Nothing says the photos are the firm's own work or that the homeowners agreed to their roofs being shown. A buyer wonders whether they will be on the website next; a competitor who knows a job can ask "did they even ask the owner?"; the Data Privacy Act makes a house photo plus a town a thin line to walk, which is why the captions carry no street and no name. Fix, after the owner answers two questions (who flew the drone, and did each customer say yes): "Our own installations, photographed by us from the air with the homeowners' agreement. We show no addresses and no names." If the drone was a hired operator, confirm the owner may use the frames on the website; if a customer has not said yes, drop that card until they do. Until the answers, the plain line from C3 claims only what is certain.

### Minor

**m1** Alt text names mango trees → "with trees and coconut palms around the house". The hero alt is good as it is.
**m2** The orange cable at the left of the array (25–28): in the hero and the share image. A buyer may ask whether an extension cord was left on the roof. Ask the owner what it is (temporary cord on the day, or the DC run in orange conduit); if temporary, a later frame would be cleaner, but 25 stays until then.
**m3** Frame 33 is served though unused (`hip-roof-town-wide-*`). Remove from `static/photos`; keep `rib-roof-eight-angle` and `three-roofs-above`, which the placements below use.
**m4** Footer fallback "Installs in Laguna and Batangas" → "the whole Philippines". About's "Where we install" → "Where we usually install" and "…Not on the list? Ask us; we go anywhere in the Philippines the roads go."
**m5** No roof on the phone's first screen: at 390 px the photo comes after the four tick points. CSS `order` on `.hero-photo` under 900 px would put it right under the lead paragraph. For the UX auditor to weigh against layout shift.
**m6** "Recent installations": nobody has said when → "Our installations" until the owner gives months.

## Selection: which frames, and which never

| Frame | Site | Verdict |
|---|---|---|
| 25 | A | Hero and share image: yes. The cleanest frame of the thirteen. Ask about the orange cable (m2). |
| 26 | A | Usable (top-down), not needed; the neighbour's blue tarp fills the corner. |
| 27 | A | Card 1 on the home page (M4); a tyre pile and a hut in the neighbour's yard at the top right are small at card size. |
| 28 | A | Spare; a rusty roof in the top left corner. Not needed. |
| 29, 30 | B | Never: installation day, hose, bin, box, rope and a bag on the roof; a legible sign on the neighbour's building. Publishing it says "this is how we leave a roof". |
| 31, 32 | B | Never: four people at the gate, plus everything in 29–30, plus a four-panel green roof that may be a neighbour's. People need a yes; drone frames of people get none. |
| 33, 34 | B | Never on the site: the neighbour's house, balcony and washing fill the top third, the cable runs are large. |
| 36 | B | Card 2, re-cropped (M2). The most relatable site for the market (a hip roof in a town street is what most ₱4,000-bill houses look like); worth keeping once the cable answer is in. |
| 35 | C | Card 3 (M3): the biggest system, green surroundings, the three-roof story. Litter in the neighbour's grass at the lower left is invisible at card size. |
| 37 | C | About page (below). |

Would a homeowner be reassured? By 25 and 27, yes without reservation. By 36, yes as "a roof like mine", with the cables and the patched sheet as the thing they would show their kumpare the electrician. By 35, impressed by the size, then "under coconut trees?" from anyone who has heard of shade. None of the three is a mistake; two need the owner's answers before they are proof rather than a question.

## Placement: where else a photo goes

Keep three cards on the home page and stop there for now; add exactly one more placement:

- About, after the first paragraph: one wide figure, `three-roofs-above` (37). Caption: "Three roofs, one property, coconut palms: the kind of roof we measure before we design." It illustrates the page's first sentence without claiming anything about the job. The two people placeholders stay until there are people photos.
- Net metering: nothing until the owner says which site is on net metering. Then 27 beside "How net metering works" with "Eight panels[, [kWp] kWp,] in [town], on net metering: the house runs on them by day, the surplus goes to the grid through the two-way meter."
- Brownouts: no roof photo; a roof says nothing about a battery. Ask the owner for a frame of a hybrid inverter and battery on a customer's wall (clean wall, cable in trunking, the brand readable). Then under "What a battery does, plainly": "The hybrid inverter and the [kWh] kWh battery on the wall of a [town] home: this is what carries the evening in a brownout."
- Estimate page: none; the form is the content and a photo pushes it below the fold on a phone.
- Thank-you page: not now. Later, a small 25 with "Your roof next." is a nice close, but it means the widget loading a website photo across origins; after the CRM items.
- A separate "Our work" page: no. Thirteen frames of three sites is a sample, not a portfolio, and a page with three entries makes the firm look smaller than the home section does. Threshold: six or more sites, each with a town, a size, a month and the customer's yes; then `/work` with one card per site and the home section shows the latest three.

## Trust: what a competitor would screenshot

In order of how easily it is done today: the "four faces" line (C1); the shade on 35 (M3); the cable runs and the yard coil in 36 (M2); "after switch-on" beside 36 (C3); the aircon brand in the share image (M5); the orange cable in the hero (m2); and, if anyone ever published them, 29–32. The one line that pre-empts most of it is M6's: own installations, own photos, homeowners agreed, no addresses. The rest is one re-crop and the owner's answers.

## Videos: what they can do, and what to film next time

Three uses, in order of value:

1. **Home page, 12 to 20 seconds, silent.** A drone orbit of site A at mid-day (the hour of 25), or the test panel being laid and read on a roof. As a muted, looping, inline video with a poster under the hero on wide screens only, MP4 (H.264) at 960 × 540, under 2.5 MB; self-hosted, because the site's content policy allows no YouTube or Facebook frames. Proves "real jobs, real roofs" in three seconds; phones get the poster (25) and no download.
2. **A Facebook post, 30 to 45 seconds, vertical (9:16).** The story the site tells in words: the roof visit with the test panel and the meter reading; the crew on the roof; the switch-on with the inverter's first kilowatts; the drone orbit. Text on screen: the town and the kWp; last card: "Free one-minute estimate, pldevinc.com/estimate". This is the "Measured roof (why us)" ad angle in docs/marketing.md, filmed instead of described.
3. **A Messenger reply, 15 seconds.** When a lead asks "may ginawa na ba kayo?", the finished roof and the inverter screen, sent with the Day-0 template. Shorter than a gallery and it answers the question that stalls bookings.

What to ask the owner to film at the next job (phone is enough; horizontal for the site, vertical for Facebook; keep the originals; write down the town and the date):
- The arrival and the test panel being carried up and laid on the roof; the meter reading with the time on screen.
- The owner saying one sentence to the customer about what the reading means.
- The crew at work on the roof. If they wear harnesses and helmets, film it; if not, do not stage it.
- The cut-over at the panel board: the moment the power goes off and comes back, so "off for a short while" has a picture.
- The switch-on: the inverter display going live, the first kW.
- The drone orbit at noon, when shadows are short; and the same orbit a week later with the roof and yard tidy.
- The customer's one sentence, only with a yes on camera or in Messenger; no faces without it; blur plates and house numbers.
Rules that carry over from the photos: no music the owner does not own, no customer name or address on screen, the town only, and nothing that shows a job unfinished as if it were done.

## Ask the owner (inputs no reviewer should invent)

1. For each site: town; panel count and wattage (or kWp); battery or net metering, and the battery's kWh; month and year of switch-on; whether the roof visit with the test panel was done; the customer's go-ahead to show the roof (town only; name never).
2. Who flew the drone (the firm, or a hired operator who agreed to website use), for the ownership line (M6).
3. Site A: what the orange cable at the left of the array is (m2); how the rails are fixed on that rib-type roof (rib clamps or through the sheet) (C2).
4. Site B: are the cables lying on the roof the final state, or were they clipped or put in conduit afterwards; is there an "after" frame; is the four-panel green roof in 31–32 the same customer's (M2)?
5. Site C: the hour 35 and 37 were shot; whether the design accounted for the palms (string layout, optimisers, trimming) (M3).
6. Next photos, in this order: the hybrid inverter and battery on a customer's wall (Brownouts); the owner on a roof visit with the test panel (About, and the hero alternative); the crew on an installation day (About); a finished roof from street level (what the neighbours see); the two-way meter (Net metering).
7. Video: the shot list above; and whether a short clip may go on the Facebook page as well as the site.

## Summary for the coordinator

1. C1: "four faces" → "Twenty panels in three groups, each fitted to its own face of the roof"; alt likewise (the count subject to the engineer's).
2. C2: drop "clamped to the framing through the sheet".
3. C3: lead → "Three of our installations, photographed from the air." until the owner confirms the visit and the switch-on per site.
4. M2/M5 re-crops: 36 `--crop 0,0.12,0.73,0.85`; 25 `--og --crop 0,0.12,1,0.82`; add `og:image:alt`; remove `hip-roof-town-wide-*`.
5. M4: card 1 → `rib-roof-eight-angle` (27) so 25 appears once; About gets `three-roofs-above` (37).
6. M6: trust line once the owner answers who flew and who agreed.
7. m4: footer fallback "the whole Philippines"; About "Where we usually install … anywhere in the Philippines the roads go". m1 "mango" out; m6 "Our installations" until dated.
8. Never publish 29–32 (clutter, a sign, people) or 33–34 (neighbour's house and washing, cables large). Keep three cards; no "Our work" page until six sites with town, size and a yes.
9. Owner questions: per site the town, kWp, battery/net metering, month, whether the test-panel visit was done, the customer's yes; who flew the drone; site A's orange cable and fixing method; site B's cables (final?) and an "after" frame; site C's hour and the shade answer.
10. Owner photos and video next: inverter + battery on a wall (Brownouts), the owner with the test panel (About/hero), the crew, street-level roof, the two-way meter; film the visit, the cut-over, the switch-on and a noon drone orbit; a 15 s silent loop for the home page, a 30–45 s vertical cut for Facebook, a 15 s reply for Messenger.
