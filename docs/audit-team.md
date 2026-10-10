# The audit team

Five standing reviewers and one writer, each a Claude Code agent definition under
`.claude/agents/`. The reviewers audit the solar engineering app, its documents and the
public website from one discipline each, and every round ends in a ranked list the owner
decides on; the writer turns the marketing specialist's brief into the customer's words.

| Role | File | What it judges |
|---|---|---|
| Cyber security | `security-auditor.md` | accounts and sessions, authorisation on every route, the public process, input handling, the Docker and tunnel deployment, dependencies |
| Solar engineer | `solar-engineer-auditor.md` | site assessment, sizing, plans, string and circuit design, quantity take-off, BOM/BOQ, program of works, Gantt, cashflow, the documents as an engineer reads them |
| Financial analyst | `financial-analyst-auditor.md` | the pricing engine against the owner's Excel workbook cell by cell: landed cost, markup tiers, the OCM share and owner's-profit balance, commission, VAT, rounding, cashflow, customer economics |
| UI/UX specialist | `ux-auditor.md` | every screen at desktop and phone width in Chromium, every document, every website page: stray elements, overflow, tap targets, wording, feedback |
| Marketing and sales | `marketing-sales-auditor.md` | the customer path from the website to the proposal: is the engineering translated into the customer's problem and its solution, honestly |
| Copywriter | `copywriter.md` | not an auditor: the team's writer. Turns the marketing specialist's angle brief into the words the customer reads (website, estimate, booking, the proposal's customer lines), selling the feeling behind the equipment inside the same honesty rails; every draft goes back to marketing for review |

## How a round runs

1. Write a round brief (the previous one is the template: what the owner said verbatim,
   the decisions in force, what changed since the last round, where the previous reports
   are, how to run the app, ports, scratch folders, the rules). Each agent reads its role
   file, then the brief, then the documents they name.
2. Start all five at once, each on its own ports and its own database, read-only on the
   repository. Each builds a realistic case with the real weather data, walks or breaks what
   its discipline covers, and writes a report with a ranked findings table on top: where
   (file:line, URL, sheet!cell or document page), what, why it matters to this owner, the
   fix, effort S/M/L, severity. Nothing fabricated; "verify" where a figure is the owner's,
   a code edition's or a datasheet's to confirm.
3. The reports are copied into `docs/audits/<round>/` and consolidated into one plan the
   owner reads: the findings that need a decision, the ones that are plain bugs, and the
   order to fix them. The owner picks the batch; the fixes follow with tests; the next round
   checks what was fixed and what was not.

Ports by convention: UX 8010/8011, marketing 8020/8021, security 8030/8031, engineering
8040/8041, finance 8050/8051 (private app / public process). The frontend `dist` is never
rebuilt during a round because every agent serves it.

## Standing constraints the team must not propose against

Customer documents carry no internal costs; warranties stay blank until the owner fills
Settings; no financing or "from ₱X a month" claims; no utility (Meralco) branding; the
server makes no outside calls (SMTP opt-in); US spelling in the owner's UI; the customer
sees "estimate", "roof check", "proposal", never "assessment"; tunnel tokens and passwords
live in `.env` only; every engine number is an editable setting with help text; the
engineering app is not a CRM or a project-management tool (the website is the start of
that pipeline, and it is a separate build).

## Rounds so far

- Round 1 and 2 (UX, marketing and copy, security, engineering): findings and their
  status in `docs/plan-engineering-app.md`, section 6.
- Round 3 (all five roles, finance new): `docs/audits/round-3/`.
- Round 4 (UX only, from the owner's screenshots: the pattern on every form,
  Settings as a menu, people and account as dialogs): `docs/audits/round-4/`.
- Round 5 (the owner's first photos on the website: marketing, UX, engineering):
  `docs/audits/round-5/`.
- Round 6 (the website's words sell the feeling: marketing's angle brief, the
  copywriter's rewrite, marketing's review): `docs/audits/round-6/`.
