# Round 8 brief: the estimate sells the feeling and the outcome, like the pages do

## What the owner said (10 October 2026, verbatim)
"awesome! just 1 final edit for the estimate page, shouldn't it be emotion driven too similar to the whole website?
Basically we sell emotions and outcome?"

The website (rounds 6 and 7) sells comfort, relief, pride, calm and control, with the equipment as the proof. The
estimate widget still speaks in the engine's words: "What goes in", "What it makes", "Used straight from the panels:
30% of what you use", "Pays for itself in", "Sized for a house using about 400 kWh a month". This round brings the
widget's every line into the same voice, without losing a single figure the engine produces.

## What the customer reads in the widget (all of it is in scope)
`frontend/src/estimate/Estimate.tsx`:
- the intro: h1 "What would your bill be with solar?" and the lead under it;
- the result: h2 "Your estimate"; the hero ("Your monthly bill", the before → after line and its sub-line, "Pays
  for itself in", "Estimated price" with "installed, with permits, VAT included", "Saved over N years" with its
  sub-line); the two actions ("Book my free on-site assessment", "Estimate another one"); "What goes in" and
  "What it makes" (`systemLine`, `coveredLine`, the net-metering and off-grid sentences); the alternative line
  ("Without the battery: …", "Add a battery for brownouts: …", the two link buttons);
- the booking card: h3 "Want the exact figure? We come and measure. The visit is free.", the hint under it, the
  field labels, the button, "Your name and a number or Messenger name are enough.", the thank-you (two paragraphs)
  and its buttons, the trust lines;
- the foot (`pld-basis`), the sticky bar ("Estimated price"), the copied summary (`summaryText`), the error and
  down notes.
`frontend/src/estimate/Wizard.tsx`: the four questions, the three goal cards (title and text), the three slider
stops (title and text), the hints on the town and usage cards, the "Use my location" line, "Next", "Back",
"Show my estimate", "Working it out…". The usage card now carries one field, the kWh on the latest bill: the
owner (10 October) had the peso-amount field removed ("it won't do help much in estimating").
`frontend/src/estimate/DayScene.tsx`: the readout parts ("Sun 1.3 kW → house 0.4 kW · battery +0.9 kW"), the
captions (`caption()`: "The house runs on the sun; the extra fills the battery.", "The battery carries the
evening.", "The grid steps in for the evening." and the rest), the build-up line "your system, piece by piece",
the "Then a typical day, hour by hour." caption, the SVG's `aria-label`, the chips.
`backend/solarapp/core/quick.py` lines 241–243: the two warnings the result can carry.
`backend/solarapp/profile.py`: the default `privacy_note` and `callback_promise` only if a word there fights the
voice (say so rather than change the meaning).

## The angle (from the website's rounds; the marketing specialist refines it in the angle brief)
- The intro asks for the feeling the visitor came with: the bill that hurts, the street going dark. The promise
  is the outcome: in a minute, the new bill, the price, the panels.
- The result opens on the outcome, in the customer's life: "Your bill: ₱4,000 → about ₱900" is already there;
  the words around it should say what that is (money that stays in the house every month), what the years add up
  to, and that the price is the whole thing, installed and papered.
- "What goes in" / "What it makes" become what the system does for the house (the panels run the house by day,
  the battery carries the evening, the extra comes back as credit), with the figures kept inside the sentence.
- The battery is comfort (the fan all night, the fridge cold, the Wi-Fi up while the street is dark); the panels
  do the saving. The alternative line sells the comfort when adding it and respects the saving when leaving it.
- The booking card sells calm and control: one free visit, the test panel on the roof, the exact proposal, you
  decide after. The thank-you sets up what happens next with a person's name when Settings carry one.
- The day scene's captions describe the family's day, not the energy balance: the morning the panels take over,
  the afternoon the meter runs backwards, the evening the battery carries, the night the grid fills in.
- The questions stay questions (the engine needs the same answers) but each can ask for the life behind it.

## Rails (nothing here moves)
- Every figure the widget shows today stays: the before and after bill, the monthly saving, the first-year saving,
  the payback, the price, the lifetime saving, the panels and kWp, the inverter kW, the battery kWh, the roof m²,
  the monthly kWh made and its percentage, the coverage percentage, the import kWh for off-grid, the CO₂, the
  typical-day figures in the readout. Rounding and `php0`/`phpAbout`/`n0`/`years` stay as they are.
- No new claim: no figure, hours of backup, brand, town, customer voice or date beyond what the engine returns and
  the facts in `docs/audits/round-7/brief.md`. No guaranteed savings, no "from ₱X a month", no financing word, no
  utility name ("your electric company"), no exclamation mark, no superlative without a figure.
- The customer reads "estimate", "roof check", "proposal". The visit is the "on-site assessment" (the owner's word;
  the only use of "assessment"). "An estimate, not a quotation" stays somewhere on the result and in the copied
  summary. A battery is comfort and backup, not savings.
- The three goal ids and the three pattern ids, every class, id, `aria-*`, `data-*`, the `pld-basis` paragraph's
  existence, the `.pld-scene-hour` and `.pld-scene-read` and `.pld-scene-cap` elements, the actions' order, the
  `#pld-book` anchor, the buttons' enabled logic and every handler stay. Words change; the machinery does not.
- The copied summary stays plain text a person can forward on Messenger: the company, the place, the system, the
  price, the bill line, the lifetime line, "an estimate, not a quotation", the links.
- The wizard's choice buttons keep a `<b>` title and a `<small>` text. The slider's stops stay three short titles
  (they share one line on a 390 px phone). The h1 fits three lines at 390 px; the lead four.
- Pinned by tests: nothing in the widget is pinned by the backend tests (`test_customer_story.py` and
  `test_documents.py` pin the proposal's line "Your estimate said about…", which is not in scope). The frontend
  must build (`cd frontend && npm run build`) and lint (`npm run lint`, baseline 7 warnings). The backend tests
  (`cd backend && SOLARAPP_DATA_DIR=/home/user/solarapp/data .venv/bin/python -m pytest -q`, 209 pass) must still
  pass if `quick.py` or `profile.py` change (`test_api.py` asserts the after-sales prefix and the warranty default).

## How to run
Private server (the result needs a signed-in user or the token; the recipe):
```
cd /home/user/solarapp/backend && SOLARAPP_DATA_DIR=/home/user/solarapp/data SOLARAPP_DB_PATH=<scratch>/app.db \
SOLARAPP_SECRET_KEY=abcdefghijklmnopqrstuvwxyz0123456789abcd SOLARAPP_APP_USERNAME=admin \
SOLARAPP_APP_PASSWORD=geo-pass-12345 SOLARAPP_COOKIE_SECURE=false SOLARAPP_STATIC_DIR=<worktree>/frontend/dist \
SOLARAPP_INTERNAL_TOKEN=geotoken123 setsid nohup .venv/bin/python -m uvicorn solarapp.main:app --host 127.0.0.1 \
--port <port> > <scratch>/server.log 2>&1 &
```
Sign in at `/` (admin / geo-pass-12345), then `/estimate`. Playwright: `NODE_PATH=/opt/node22/lib/node_modules node
script.js`, Chromium preinstalled; a walk script to copy is
`/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/geo/flow2.js`. Ports: marketing 8211,
copywriter 8212. Scratch: `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents8/`.
The frontend's venv for the backend is `/home/user/solarapp/backend/.venv`; `npm run build` in the worktree's
`frontend` needs `node_modules` (copy or symlink from `/home/user/solarapp/frontend/node_modules`).
Implementation agents commit on their worktree branch with exactly these two trailer lines and never push:
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014X7mTiayp7JMJuZqc5cDaJ

## The round
1. Marketing: the angle brief for the widget, section by section (the feeling, the outcome, the proof at hand, the
   objection, the words to avoid), plus the lines that cost a sale today, in rank order with the replacement.
2. Copywriter, in a worktree, with the angle brief: every line above, before and after, the angle it serves.
3. Marketing reviews the draft line by line (accept / change to / must go). The coordinator merges, walks the
   flow at 390 and 1280, records the round.
