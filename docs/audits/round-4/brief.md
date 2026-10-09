# Round 4 brief: Facebook-level easy (UX audit, then two fix batches)

## What the owner said (verbatim, 9 October 2026, with eight screenshots)
"these are some of the things I've seen that are aesthetically wrong" (screenshots 14-18), then:
"For the panel, make it automatic done on the background and the section remove in data entry. For the aesthetic,
I think you can see the pattern that I am telling you to fix through the screenshots I gave you? As for the
tagging, is this really necessary for the part of the Engineering/Technical team? Also, the user management is
really not intuitive. Run the relevant agents, I want the user experience to feel like I am just browsing
Facebook-level easy."

The screenshots (open them with the Read tool; they are the standard of what the owner calls wrong):
(owner screenshot 14)  Settings › Pricing › Ground work, Hauling, Crew transport, Tools: raw 13-decimal rates, a bare JSON box for the tasks, no units on man-hour fields, a spinner on one field only
(owner screenshot 15)  Payment terms: the label repeated above the box heading, milestone names cut off, the installments row's fields and labels not lined up with Add milestone
(owner screenshot 16)  "Power off on installation day": a short field with a help text five times its width stacked into a tall column
(owner screenshot 17)  Minimum task durations: lowercase row names, no "minutes" on the table while the neighbour has one, the two blocks on no common grid
(owner screenshot 18)  Savings settings: help texts of very different lengths leaving ragged gaps, units cut off ("₱ including…", "% of contra…", "kg CO2 per …"), spinners on some fields
(owner screenshot 19)  Panel options card on the On site step (the owner wants the panel chosen automatically in the background and this card gone from data entry)
(owner screenshot 20)  System losses: units cut off ("% of energy…"), one help text four times longer than the others
(owner screenshot 21)  The job-stage pill on the project head (Assessed, Quoted, Signed, Sourcing, Installing, Commissioned, Net metering, Closed) that the owner questions for an engineering team

## The pattern, in the owner's sense
Every screen must be scannable without thinking: a number reads as a person would say it (no 13-decimal floats; a
sensible number of decimals per quantity), every number has its unit and the unit is never cut off, a help text is
one short line (or a "?" that opens the long one), labels and inputs sit on one grid with equal rows, a block has
one heading not two, nothing is a JSON box, capitalisation is consistent, spinner arrows are either everywhere or
nowhere (nowhere), nothing is truncated with "…", and a form never asks for something it could know. "Facebook-level
easy": the next thing to tap is obvious, an action asks for what it needs at the moment of the action (a dialog),
and there is no standing form you must fill before a button works.

## The repository and how to run (unchanged from round 3)
/home/user/solarapp on branch claude/wonderful-maxwell-wawb8t (the audit team's round 3 and its fix batches are
merged; read docs/audits/round-3/00-plan.md and DECISIONS.md "The clean form" for what was just done and why).
Python: /home/user/solarapp/backend/.venv/bin/python. Tests: cd backend && pytest -q (191 pass with
SOLARAPP_DATA_DIR=/home/user/solarapp/data). Frontend: cd frontend && npm run build (tsc -b) and npm run lint.
Playwright scripts run from /home/user/solarapp; Chromium preinstalled; map tiles blocked.
Private app on your port with your database:
  cd <repo>/backend && SOLARAPP_DATA_DIR=/home/user/solarapp/data SOLARAPP_DB_PATH=<scratch>/app.db SOLARAPP_SECRET_KEY=r4-secret-key-32-characters-long-xxxxx SOLARAPP_APP_USERNAME=admin SOLARAPP_APP_PASSWORD=round4-pass-123 SOLARAPP_COOKIE_SECURE=false SOLARAPP_STATIC_DIR=<repo>/frontend/dist SOLARAPP_INTERNAL_TOKEN=r4token123 setsid nohup /home/user/solarapp/backend/.venv/bin/python -m uvicorn solarapp.main:app --host 127.0.0.1 --port <PORT> > <scratch>/private.log 2>&1 &
Stop it with the pids from `pgrep -f "port <PORT>"` run from a shell whose own command line does not contain that
string; never a bare pkill on uvicorn (other agents run at the same time).
A seed that builds a calculated project with the real weather, a stale one, an uncalculated one and two engineers:
/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/final3/seed.py (edit BASE, the password and the OUT path).
Ports: ux audit 8010; engineering batch 8150; polish batch 8160. Scratch: /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents4/ux/, .../impl4/engineering/, .../impl4/polish/.

## Standing constraints
Customer documents carry no internal costs; no financing or "from ₱X a month" claims; no utility (Meralco)
branding; the server makes no outside calls; US spelling in the owner's UI; the customer sees "estimate", "roof
check", "proposal", never "assessment"; secrets only in .env; every engine number is an editable setting with help
text; the engineering app is not a CRM or PM tool; nothing fabricated; no model names anywhere in code, comments,
docs or commit messages. Implementation agents commit on their worktree branch with these two trailer lines, exactly,
and do not push:
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_014X7mTiayp7JMJuZqc5cDaJ

## Added by the owner after the round started (verbatim)
"The settings page could also do a revamp, instead of 1 continuous form like, why not show what's only relevant to
the menu you already created?"
Meaning: Settings is no longer one long page. The section index becomes the navigation: picking an entry shows
that section alone (its own route, so a link and the browser's back button work), on the desk as a left menu with
the one section beside it, on the phone as a list of sections that opens one at a time with a back link. The
pricing groups are entries of their own. Nothing else is on the screen but the section the person chose.
