# Round 7 brief: a marketing website, not a blog

## What the owner said (10 October 2026, verbatim, on seeing the live site)
"I think some things that you are trying to put in there are have put in there is anti marketing or sales meaning
it might be the reason why the customer might not go with us, can you review? The no address no names might signal
a made up or grabbed photos, this was supposed to be testimonies or proof right? Then the one on the photo I
attached, it feels it is missing something "years" what? and then there are broken sentences that doesn't make
sense and then the website looks like a blog rather than a marketing website. There is no agreement needed
because those are my homes, the biggest install is where me and my family live, the white roof is my wife's
inherited family house from her mother, and the small brown roof is the house of my parents."
Then: the after-sales line should "say we provide after sales support" and "respond in the earliest humanly
possible", not a schedule; the About page's town list "is really off for a marketing standpoint"; and of the three
option cards: "Isn't it better to ask for their emotion than solar with net metering, battery, back up nothing is
sold?"

## What the coordinator already changed (commits 34abdc6 and after; the baseline this round starts from)
- The installations section is proof, not a gallery: "Our own roofs first. We live with what we sell. The owner's
  home, the owner's parents' house and the family's house in Quezon City, photographed by us from the air." Each
  card is headed by whose house it is and where; the captions no longer list what a system lacks.
- The option cards ask for the feeling ("I just want a lower bill." / "I want the lights on when the street goes
  dark." / "I want my roof to run my house.") with the system kind as the small label underneath.
- The clauses that undercut the sale went: "No battery, so no power during a brownout" (now "A battery can be
  added later if you want lights in a brownout too"), "The battery is for comfort, not savings, and we say so"
  (now "The panels bring the bill down; the battery buys the comfort"), "No battery means no backup. We say it
  before you buy:" (now "Want lights in a brownout too?"), "and we say so" everywhere, "The town, never the
  address or the name", the shade sentence on the owner's home.
- Fragments became sentences; the hidden "years" tile stays hidden while the performance-warranty years are
  blank (a script bug); the after-sales profile line reads "After switch-on you are not on your own: call or
  message us and we answer as soon as humanly possible."; About's town list is one sentence.

## The facts in force (nothing beyond them may be claimed)
The three homes: the owner's own home in Pila, Laguna (13.75 kWp across three roofs, a 30 kWh battery, a 12 kW
hybrid and a 6 kW grid-tie inverter, net metered since 2023, more than ₱33,000 of credit on the bill; the house
runs through brownouts); the owner's parents' house in Pila, Laguna (8 panels, 4.56 kWp, a 6 kW grid-tie inverter,
early 2026; no bill story: the household added appliances); the owner's wife's family house in Fairview, Quezon
City (16 panels, 9.12 kWp, a 12 kW hybrid inverter without a battery, early 2026; nobody lives there day to day).
No before-and-after bill exists for any of them. The switch-over time is not on a datasheet ("by itself" stays).
Typhoons: the fixing and "the oldest installation, from 2023, has stood through every typhoon season since". The
panel performance warranty defaults to 25 years in the profile. Warranties and contact details come from the
profile at page load; the net-metering example (500 kWh a month in Tanauan: 4.1 kWp, 7 panels, about ₱193,000,
under 4 years, about two thirds off) is the engine's. The owner answers after-sales as above. No financing, no
guaranteed savings, no utility name, "estimate", "roof check", "proposal".

## What this round must deliver
1. Marketing and sales: an anti-sales audit of every page and the estimate widget's texts: every line that could
   make a buyer walk away, in rank order, with the replacement; and the proof the site is not yet using (the
   owner's own roofs, since 2023, the credit, the engineer's seal, the papers filed, the free visit).
2. UX, as the designer this time: make the pages read as a marketing website. A visitor on a phone from a
   Facebook link must see, in order: a roof, a promise, a button; then proof; then the three wants; then how it
   works; then the questions; then the button again. Fewer and shorter text blocks, bigger photos, a proof strip,
   section rhythm, the call to action visible on every screen, the installations as testimony cards, the FAQ
   compact. Implementation in a worktree: HTML structure and CSS, the copy kept or shortened, never a new claim.
3. Copywriter: on the merged design, with the marketing audit in hand: headlines that ask for the feeling, body
   copy in complete sentences, the honesty inside the sentence not bolted on after it, nothing that reads like a
   disclaimer; every number the site carries kept.
4. Marketing reviews the result line by line; the coordinator merges, walks the pages, records the round.

## How to run
Built site: `python site/build.py` (`/home/user/solarapp/backend/.venv/bin/python`); site tests `cd backend &&
pytest -q tests/test_site.py`; serve `site/dist` with `python3 -m http.server <port> --bind 127.0.0.1`; Playwright:
`NODE_PATH=/opt/node22/lib/node_modules node script.js`, Chromium preinstalled. The profile fetch 404s on a static
server (the `is-empty` fragments stay hidden; the warranty cards too). Ports: marketing 8201, UX 8202, copywriter
8203. Scratch: /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents7/{marketing,ux,copy}/.
Implementation agents commit on their worktree branch with exactly these two trailer lines and never push:
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014X7mTiayp7JMJuZqc5cDaJ

## Standing constraints
Nothing fabricated; no financing or "from ₱X a month"; no utility branding; "estimate", "roof check", "proposal";
the three system kinds keep their names as the small labels; the `data-profile` hooks and the placeholder markers
stay; the strings `backend/tests/test_site.py` pins stay or the test changes with them; no model names anywhere.
