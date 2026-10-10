# Round 6 brief: the website's words sell the feeling

## What the owner said (10 October 2026, verbatim)
"Also I want the marketing and the copywriter to work together and instead of full solar terms let's make it so
that it will sell emotions, for example the battery = comfort is a good start."

## The facts in force (the owner's answers of 10 October; nothing beyond them may be claimed)
- The rib roof (home card 1): 8 panels, 4.56 kWp, a 6 kW grid-tie inverter, no battery, not on net metering,
  installed early 2026. The orange run is the PV-wire conduit; the rails sit on L-feet fixed through the sheet.
- The hip roof (card 2): 16 panels, 9.12 kWp, a 12 kW hybrid inverter with no battery attached, not on net
  metering, installed early 2026. The black runs are HDPE conduit, the final state.
- The three roofs (card 3 and About): 13.75 kWp, a 30 kWh battery, a 12 kW hybrid inverter and a 6 kW grid-tie
  inverter carrying a 5.5 kWp part of the array; net metered since 2023; ₱33,568.72 of credit accumulated
  (printed as "more than ₱33,000"); photographed between nine and ten in the morning; "the design provided extra
  panels so that shadings will not bring the production down too much".
- These are family homes; the test-panel roof visit did not yet exist when they were designed, so no page says
  they were measured first. The owner flew the drone. No towns were given: no card names one.
- The net-metering page's example (500 kWh a month in Tanauan, Batangas: 4.1 kWp, 7 panels, about ₱193,000, under
  4 years, about two thirds off the bill) comes from the engine and stays unless the engine changes it.
- Warranties (12 years panels, 5 battery, 5 inverter, 2 workmanship) and contact details come from the profile at
  page load through the `data-profile` hooks; the pages never hard-code them.

## The pages
`site/pages/index.html`, `brownouts.html`, `net-metering.html`, `about.html`, `estimate.html` (frame only),
`privacy.html` (legal: leave it), `404.html`; the frame `site/layout.html` (header tag line, footer). The estimate
widget's own texts (`frontend/src/estimate/Estimate.tsx`: the questions, the result, the booking form, the
thank-you) are customer copy too: propose them in the report with file and line; the coordinator applies them,
because that build has its own tests.

## How the round runs
1. Marketing and sales writes the angle brief (read-only): per page and section, the feeling to sell, the proof
   the facts allow, the objection to pre-empt, the words to avoid, the line to keep as is. Scratch:
   /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents6/marketing/; report → `docs/audits/round-6/marketing-brief.md`.
2. The copywriter rewrites the pages in a worktree from that brief, builds the site, runs the site tests, commits
   on the worktree branch with the trailer lines (never pushes) and reports before/after per section.
3. Marketing reviews the worktree's pages line by line (read-only) and the copywriter revises; disagreements go
   to the coordinator with both texts. The coordinator merges, walks the pages, records the round in DECISIONS.

## Standing constraints
Nothing fabricated; no guaranteed savings, no "from ₱X a month", no financing; no utility branding; "estimate",
"roof check", "proposal", never "assessment"; the three system kinds keep the estimate's names; a battery is for
comfort and backup, not savings; the HTML structure, classes, ids and `data-profile` hooks stay; no model names
anywhere in code, docs or commits. Implementation commits end with exactly these two lines:
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014X7mTiayp7JMJuZqc5cDaJ
