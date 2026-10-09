# Round 3 brief for the audit team (shared by all five agents)

## What the owner said (verbatim)
"I think we need to build a whole team of agents for audits, for the solar app:
1. Cyber Security
2. Solar Engineer (to produce the plans and quantity take offs etc)
3. Financial Analyst (for pricing validation - I am not sure if you've carried over the excel boq logic
   particularly the different percentage of OCM and Owner's Profit balance etc)
4. Ui/UX Specialist because I still some odd sticks popping out here and there.
5. Marketing and Sales specialist so that it can translate the quantity take offs and plans to something
   that the customer would really care about and provide a solution to their problem.
Note: The leads tab should not be in the solar engineering app.
Once we have this down we can work on the website as starting line for the leads and crms, and project
management, finance etc."

Owner: PL Development Inc., a solar installer in Pila, Laguna, Philippines; service area Laguna and
Batangas. The owner and one or two engineers use the back office (solar.pldevinc.com, live) on a phone on
roofs and a laptop in the office. The public website (pldevinc.com, live) carries a four-question estimate
and a booking form.

## The decision in force this round
The engineering app (solar.pldevinc.com) is a solar engineering app only. The Leads tab is leaving it: the
website bookings (`/api/leads`, table `leads`) stay as the data a future CRM will own, and the engineering
app keeps only the hand-off (start a project from a booking). Do not audit the Leads page as a feature of
the engineering app; do audit the hand-off, the booking data, and anything else that still smells of CRM
or project management inside the engineering app, and say so with the tag [crm] or [pm].

## Your role
Your standing role, checklist and rules are in /home/user/solarapp/.claude/agents/<your file>.md. Read it
first, then this brief, then the documents it names.

## What changed since the previous round (git log, newest first)
- People with their own accounts: owner and engineer roles, per-person authenticator and keys
  (argon2 passwords, temporary-password gate, People card, Your account card, server CLI
  `python -m solarapp.users`; `.env` password only creates the first owner).
- Pricing keeps an inverter on a pre-update database; Docker build passes the website address.
- The owner's corrections: "off-grid" means no export with the grid as backup (import billed, nothing
  sold); the Felicity eco-hybrid exports and is the default again; a late finish stays one day.
- Design and outputs: seven cards with an index, a documents card, the stage pill, drafts saved on first Save.
- Engineering numbers: losses at the meter, the hourly-year battery with days of autonomy, the
  grid-interactive inverter rule, task floors.
- Plan drawings per face, the Gantt chart, the BOM export (CSV/XLSX).
- Leads separated from projects (stages assessed…closed on projects; the inbox has its own stages).
Read DECISIONS.md from "Security (from the security audit)" to the end for the reasons.

## The previous round's reports (read the one for your discipline; check what was fixed and what was not)
/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/audits2/{security,engineering,ux,marketing}.md
and the plan that came out of them: /home/user/solarapp/docs/plan-engineering-app.md (section 6 lists each
finding and its status). The finance role is new this round: nothing to re-check.

## The repository
/home/user/solarapp on branch claude/wonderful-maxwell-wawb8t. Read first: README.md, DECISIONS.md,
docs/security.md, docs/marketing.md, docs/plan-engineering-app.md. Backend: backend/solarapp (FastAPI,
SQLModel, pvlib, ReportLab). Frontend: frontend/src (React 19, Vite; dist already built at
frontend/dist, do NOT rebuild it, other agents serve it). Website: site/pages/*.html, built into site/dist
(already built). Public process: backend/solarapp/public.py.

## Running things (use YOUR ports and YOUR scratch folder; the other four agents run at the same time)
Python venv: /home/user/solarapp/backend/.venv/bin/python (all deps installed; openpyxl, playwright too).
Weather data (real PVGIS download): /home/user/solarapp/data (read it, never write there).
Materials workbook: /home/user/solarapp/backend/data_seed/PLD_Materials_DB.xlsx (the app seeds itself
from it on first start).

Private app (back office):
  cd /home/user/solarapp/backend && SOLARAPP_DATA_DIR=/home/user/solarapp/data \
  SOLARAPP_DB_PATH=<your scratch folder>/app.db SOLARAPP_SECRET_KEY=audit-secret-key-32-characters-long-xx \
  SOLARAPP_APP_USERNAME=admin SOLARAPP_APP_PASSWORD=audit-pass-1 SOLARAPP_COOKIE_SECURE=false \
  SOLARAPP_STATIC_DIR=/home/user/solarapp/frontend/dist SOLARAPP_INTERNAL_TOKEN=audittoken123 \
  setsid nohup .venv/bin/python -m uvicorn solarapp.main:app --host 127.0.0.1 --port <PRIVATE_PORT> \
  > <your scratch folder>/private.log 2>&1 &
Sign in: username admin, password audit-pass-1 (the first owner; no authenticator yet). Add an engineer
under Settings › People to test the roles, or with the CLI:
  SOLARAPP_... (same env) .venv/bin/python -m solarapp.users create juan --name "Juan" --role engineer

Public app (the website + estimate, forwards to the private app):
  cd /home/user/solarapp/backend && SOLARAPP_DATA_DIR=<your scratch folder> SOLARAPP_SITE_DIR=/home/user/solarapp/site/dist \
  SOLARAPP_STATIC_DIR=/home/user/solarapp/frontend/dist SOLARAPP_UPSTREAM=http://127.0.0.1:<PRIVATE_PORT> \
  SOLARAPP_INTERNAL_TOKEN=audittoken123 setsid nohup .venv/bin/python -m uvicorn solarapp.public:app \
  --host 127.0.0.1 --port <PUBLIC_PORT> > <your scratch folder>/public.log 2>&1 &

To stop your servers: kill the pids from `pgrep -af "port <PRIVATE_PORT>"` (never a bare pkill on
"uvicorn": the other agents' servers would die too).

Tests: cd /home/user/solarapp/backend && .venv/bin/python -m pytest -q   (155 pass today; read-only use).
Playwright: node scripts run from /home/user/solarapp (require('playwright') works there); Chromium is
preinstalled. Examples: /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/pw/*.js.
Map tiles (openstreetmap) are blocked in this sandbox: ignore those console errors.

Ports: security 8030/8031. engineering 8040/8041. finance 8050/8051. ux 8010/8011. marketing 8020/8021.
Scratch folder: /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents3/<name>/
(name = security | engineering | finance | ux | marketing).

## Rules (all agents)
- Read-only on the repository: do not edit, commit or push anything under /home/user/solarapp, and do not
  rebuild frontend/dist or site/dist. Scripts, screenshots and databases go in your scratch folder only.
- Every finding cites where (file:line, URL, sheet!cell or document page), what is wrong, why it matters
  to this owner, the fix you propose, an effort tag S/M/L and a severity. Rank by severity. Do not pad.
- Tag each finding: [engineering] [finance] [security] [ux] [sales] [copy] [website] [crm] [pm] [bug].
- Nothing fabricated: no invented regulations, clause numbers, numbers or claims. When unsure, say "verify".
- Standing constraints of this product (do not propose the opposite): customer documents carry no internal
  costs; warranties stay blank until the owner fills Settings; no financing or "from ₱X a month" claims;
  no utility (Meralco) branding; the server makes no outside calls (SMTP opt-in); US spelling in the
  owner's UI; the customer sees "estimate", "roof check", "proposal", never "assessment"; tunnel tokens
  and passwords live in .env only; every engine number is an editable setting with help text.
- Write your report to /tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents3/<name>.md
  (markdown, with a ranked findings table at the top and the detail below), stop your servers, and finish
  with a 15-line summary in your reply: the verdict, the top five findings with severity, and what is sound.
