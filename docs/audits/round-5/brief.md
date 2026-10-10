# Round 5 brief: the first real photos on the website

## What the owner said (10 October 2026)
"if I give you videos and photos, would you be able to use it along with the agents to work on the website?" Then
thirteen drone photos in three batches ("I'll add 8 more pictures, let me finish uploading before you work on it,
I am not sure how we can work on the videos"). No towns, system sizes or customer consents were given with them.

## The photos
Originals (session scratch, not in the repository): /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/site-photos/originals/25.jpg … 37.jpg
Three sites, as far as the frames show:
- Site A, 25–28 (1500 × 1125): eight panels in two rows of four on a maroon rib-type roof, a field and trees around, an aircon unit on the wall. 25 wide, 26 top-down, 27 and 28 angled. Finished and clean.
- Site B, 29–34 and 36 (2000 × 1500 and 1500 × 1125): a grey corrugated hip roof in a built-up street. 29–32 are from installation day (hose, box, rope and bin on the roof; 31 and 32 show four people at the gate); 33, 34 and 36 show the finished array (about twenty panels on four faces) with the cable runs visible on the roof surface. A neighbour's green roof with four panels appears in 31 and 32.
- Site C, 35 and 37 (1500 × 1125): a larger array over the main house, an annex and a smaller roof of one property, coconut palms shading part of the array at the time of the shot. 35 angled, 37 top-down.
Web versions already made (site/tools/photos.py: exact 4:3 crops at 960 and 480 px, WebP and JPEG, metadata dropped) in site/static/photos/: rib-roof-eight (25), rib-roof-eight-angle (27), hip-roof-town (36, cropped to lose most of the neighbour's house), hip-roof-town-wide (33), three-roofs-palms (35), three-roofs-above (37), and og-home.jpg (1200 × 630 from 25).

## What is on the site now (the baseline to audit)
- Home: a photo (25) beside the hero text from 900 px, under it on a phone; "Recent installations" with three real cards (25, 36, 35) and captions written only from what the frames show; the roof-visit card still a placeholder the public build drops.
- Every page's share image (og:image) is og-home.jpg instead of the icon.
- Nothing on About, Brownouts, Net metering or Estimate yet. No people photos exist (the About placeholders for the owner and the crew stay).
Built site: /home/user/solarapp/site/dist, served read-only at http://127.0.0.1:8195 (a static server, so the profile fetch 404s and the estimate widget cannot run; both out of scope). Preview with placeholders: python site/build.py <scratch>/dist-preview --with-placeholders, served on your own port.

## Deliverables
Each auditor writes <scratch>/report.md; the coordinator copies it into docs/audits/round-5/. Read-only: never modify, commit or push the repository. Scratch: /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents5/{marketing,ux,engineering}/.
- Marketing and sales: the selection, the captions, the placement, the share image, what to ask the owner.
- UX: the home page and the other pages at 1280 and 390 (and the widths where the hero grid turns), the cards, loading, layout shift, the preview with placeholders.
- Solar engineer: what each frame shows to a knowledgeable buyer, a competitor or a PEE; which frames to publish and which not; what a caption may truthfully claim; panel counts.

## Standing constraints
Nothing fabricated: no town, size, brand or customer name the owner has not given; no financing or "from ₱X a month"; no utility branding; "estimate", "roof check", "proposal", never "assessment"; no model names anywhere in code, docs or commits.
