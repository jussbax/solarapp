# Security audit — round 3 (solarapp)

Reviewer: "security". Date: 2026-10-09. Branch `claude/wonderful-maxwell-wawb8t`.
Ports: 8030 (private), 8031 (public), both started per the brief and **stopped** at the end.
Scratch: `/tmp/claude-0/-home-user/2a22d1e9-a264-58af-86c3-f169033ed722/scratchpad/agents3/security/`.

Scope this round: the **new accounts/people system** (`auth.py`, `api/users.py`, `users.py` CLI,
`models.User`/`Passkey`), with a full re-check of the areas the round-2 report flagged
(session cookie, passkeys, two-factor, body caps, embed CSP, public-process trust) and the
CRM/PM boundary the round-3 brief calls out (the leads hand-off).

Method: read every backend module in scope; ran live probes with `httpx`/`curl` against my own
servers and in-process concurrency tests against the app's own modules. Every probe is in the
Probe log, with the script that produced it.

**Headline: the app remains genuinely well-hardened — no critical and no high findings.**
Every round-2 finding (H1 cookie password-fingerprint, M1 backup-code race, M2 stolen-cookie key
management, M3 session revocation, L3 body cap, L5 embed CSP) is **fixed, and I confirmed each one
live**. The new per-person accounts model (argon2id passwords, per-user `session_generation` HMAC
cookie, server-enforced owner/engineer split, step-up for key/authenticator management,
last-owner guard, temporary-password gate) holds up under probing. What remains is two low-severity
items (a cross-lock data race, and the leads/PII boundary) plus informational notes.

---

## Findings (ranked)

| # | Sev | Tag | Where | What |
|---|-----|-----|-------|------|
| 1 | low | [security][bug] | `api/auth_routes.py:74-82` + `api/quick_routes.py:95-119` | `_hits` dict written under two different locks → `dictionary changed size during iteration` crash (500 / mild self-DoS) |
| 2 | low | [crm][security] | `api/leads.py:36` | Full leads inbox (all customer PII + delete) lives in the engineering app, open to every engineer; exceeds the in-force "hand-off only" boundary and widens DPA exposure |
| 3 | info | [security] | `docs/security.md`, `DECISIONS.md` "round two"; `api/auth_routes.py:138-141` | Doc drift: session nonce is now a per-user DB column, not `data/session.key`; password-change message overstates ("not used before" blocks only the current password) |
| 4 | info | [security] | `Dockerfile:2,15`; `docker-compose.yml:` cloudflared tag | Supply-chain pinning still partial (node + cloudflared mutable tags; pip not `--require-hashes`) — unchanged since round 2 |
| 5 | info | [security] | `backend/requirements.lock`, `frontend/package-lock.json` | Dependency advisories cannot be confirmed offline — **verify** with `pip-audit` / `npm audit` |

---

### LOW

**1 — Cross-lock data race on the rate-limit dict `_hits` (sporadic 500 / mild self-DoS).**
`backend/solarapp/api/auth_routes.py:74-82` (`_options_allowed`) and
`backend/solarapp/api/quick_routes.py:95-119` (`_throttle`/`_sweep`) · tag **[security] [bug]** · effort **S**
The anonymous passkey-options limiter (`_options_allowed`) mutates **`quick_routes._hits`** while
holding **`auth_routes._lock`**; the public-estimate limiter (`_throttle` → `_sweep`) mutates and
**iterates the same `_hits` dict** while holding a **different** lock, `quick_routes._lock`. The two
locks do not exclude each other, so `_sweep`'s `[k for k, q in _hits.items() …]` can run while
`_options_allowed` inserts a new `pk:<ip>` key, raising
`RuntimeError: dictionary changed size during iteration`. That is an unhandled 500 for whichever
request is mid-sweep.
- Reproduced (in-process, against the app's own modules): `auth_routes._lock is quick_routes._lock → False`,
  `auth_routes._hits is quick_routes._hits → True`; 4 threads inserting `pk:<n>` keys under the auth
  lock while 4 threads swept under the quick lock produced **204** `dictionary changed size during
  iteration` errors in 2 s. See Probe log P-LOCKRACE. (I did **not** reproduce it over HTTP — the
  per-IP rate limits and timing make the window hard to hit from one address; the in-process test is
  the proof of the shared-object/two-locks condition that the live handlers run.)
- Impact for this owner: an anonymous caller driving `/api/auth/passkey/options` from several
  addresses at the same time as public estimate traffic can make estimate or login requests fail
  intermittently with a 500. No auth bypass and no data corruption — a reliability/annoyance issue,
  not a breach. Low.
- Fix: guard `_hits` with **one** lock (share `quick_routes._lock` in `_options_allowed`), or give the
  passkey-options limiter its own `dict` + `Lock` instead of reusing `quick_routes._hits`.

**2 — The whole leads inbox (customer PII + delete) is in the engineering app and open to every engineer.**
`backend/solarapp/api/leads.py:36` (`dependencies=[Depends(require_user)]`) · tag **[crm] [security]** · effort **M**
The round-3 decision in force is that the engineering app keeps **only the hand-off** ("Start
assessment" from a booking); the leads table is data a future CRM will own. But the router still
exposes the full inbox — `GET /api/leads`, `GET /api/leads/{id}`, `GET /api/leads/funnel`,
`PATCH /api/leads/{id}`, `DELETE /api/leads/{id}` — gated only by `require_user`, so **any engineer**
(not just the owner) can list and read every website lead's **name, contact, address and precise
GPS pin**, edit them, and **delete** lead records.
- Verified (live): engineer `juan` (role=engineer) got **200** on `GET /api/leads`; the owner's People
  endpoints correctly returned **403** to him (Probe log P2b), so the role machinery works — the leads
  routes simply do not use it.
- Impact for this owner: this is personal data under the Data Privacy Act. The hand-off needs only
  `POST /api/leads/{id}/convert` (and perhaps a read of the one lead being converted). Keeping the
  whole inbox, its PII and a destructive `delete` available to every engineer inside the engineering
  app both contradicts the stated boundary and widens who can read/erase customer PII. Risk is
  tempered by the tiny, trusted team, hence low — but it is a governance/DPA gap worth closing.
- Fix: restrict `list/get/patch/delete/funnel` to `require_owner` and leave only `/convert` (and the
  single-lead read it needs) on `require_user`; or move the leads router out of the engineering app
  entirely, as the decision intends, when the CRM module lands.

### INFO

**3 — Doc drift on session revocation, and an over-stated password message.**
`docs/security.md`, `DECISIONS.md` ("Security, round two") · `api/auth_routes.py:138-141` · **[security]** · effort **S**
`DECISIONS.md` "round two" and `docs/security.md` describe the session nonce as living in
`data/session.key`, rotated by "Sign out everywhere". The shipped accounts model (correctly described
in `DECISIONS.md` "Accounts") instead keys the cookie HMAC on the **per-user `User.session_generation`
column** in `solarapp.db` — there is no `session.key` file. No operational risk (the DB is already in
the nightly backup, and revocation works — verified in P8/P9), but the "what to back up / how a
session is killed" wording is stale and should be reconciled to the per-person column. Separately,
`change_password` rejects only the **current** password while telling the user to "Choose a password
you have not used here before" — there is no password history, so the message overclaims; either
reword it or add history.

**4 — Supply-chain pinning still partial (unchanged from round 2).**
`Dockerfile:2` (`node:22-alpine`), `Dockerfile:15` (python base digest-pinned ✓), compose
`cloudflare/cloudflared:2026.10.0` · **[security]** · effort **S**
The python base is digest-pinned (good); `node:22-alpine` (build stage) and the cloudflared image use
mutable tags, and `pip install -r backend/requirements.lock` is not `--require-hashes`. A poisoned
build-stage image could taint the frontend bundle. Pin both by digest when bumping them monthly and
consider hash-locking pip, as the round-2 report already recommended.

**5 — Dependency advisories: verify, not confirmable offline.**
`backend/requirements.lock`, `frontend/package-lock.json` · **[security]** · effort **S**
The lock pins versions beyond my offline knowledge (e.g. `cryptography==50.0.2`, `fastapi==0.142.2`,
`SQLAlchemy==2.1.3`, `pydantic==2.13.5`, `webauthn==3.0.1`, `argon2-cffi==25.1.0`, `reportlab==5.0.1`,
`pillow==12.3.0`, `starlette==1.7.0`). I cannot assert any specific advisory without network access.
**Verify** monthly with `pip-audit -r backend/requirements.lock` and `npm audit --omit=dev`, as
`docs/security.md` already instructs.

---

## Round-2 findings — re-verified FIXED (live where marked ✓live)

- **H1 (cookie leaked `sha256(password)[:12]`): FIXED.** The cookie payload is now
  `{"id","u","g"}` with `g = HMAC-SHA256(secret_key, "{id}|{session_generation}|{password_hash[-24:]}")[:16]`
  (`auth.py:79-85`). ✓live: decoded my live owner cookie → `{"id":1,"u":"admin","g":"0deb515bad534695"}`;
  `g` is 16 hex (keyed), and it is **not** `sha256(<any candidate password>)[:12]` (P1).
- **M1 (backup code redeemable concurrently): FIXED.** `twofactor.verify` now does
  `session.refresh(user)` and the whole check-consume-write **inside** `_lock` (`twofactor.py:101-135`).
  ✓ 16 threads with the same backup code → **1/16** accepted, 7 codes left; TOTP replay guard holds
  (P-CONC).
- **M2 (stolen cookie could manage keys): FIXED.** `/passkeys/options`, `/passkeys/{id}/remove`,
  `/totp/begin`, `/totp/disable` all call `_step_up` (password + fresh code). ✓live: cookie-only, no
  password → **403** "Confirm with your password"; with the password → 200 (P3). Register has no second
  step-up by design — the challenge is issued only after a step-up, is bound to the user id, single-use
  and 5-min (`passkeys.py:93-104`, `auth_routes.py:230-238`).
- **M3 (no server-side revocation): FIXED (per-person).** Password change, role change, deactivation,
  owner reset and "sign out everywhere" each rotate `User.session_generation`, invalidating the HMAC
  on every existing cookie of that one person. ✓live: cookie stale after a password change → **401**
  (P8); a signed-in engineer's cookie died the instant the owner deactivated him, and stayed dead after
  reactivation → **401** (P9). (Plain logout is still per-device by design — documented.)
- **L3 (no private body cap): FIXED.** `MAX_BODY=1 MB` (`main.py` body_cap middleware). ✓live:
  1 MB `customer_name` → **413**; chunked/no-length write → **411**; normal write → 201 (P4).
- **L5 (private `/estimate` had no CSP/XFO): FIXED.** `/estimate` now carries the embed CSP
  (`frame-ancestors 'self' <origins>`), while `/login` and `/` carry the office CSP + `X-Frame-Options:
  DENY`. ✓live (P5).
- **L1/public visitor address: FIXED.** The public proxy copies `cf-connecting-ip` only from a trusted
  (private/loopback) peer (`public.py:88-96`); the private app honours proxy headers only from trusted
  peers (`quick_routes.client_ip`). ✓live: private `/api/quick/*` with no/wrong token → **404**, right
  token → 200; the public process blocks every non-quick `/api/*` → 404 and caps bodies at 16 KB → 413
  (P11).

## What is sound (do not touch)

- **Role split, enforced on the server.** Engineer `juan` → **403** on `GET/POST /api/users`,
  `PUT /api/settings`, `PUT /api/pricing/config`, `DELETE /api/pricing/items/*`; **200** on
  `/api/assessments`, `/api/leads`, `/api/pricing/items`. Owner-only is `dependencies=[require_owner]`;
  the last-active-owner guard and the self-demote/deactivate guard are present (P2b).
- **Accounts.** argon2id hashes; `.env` password used once to bootstrap the first owner then
  ignorable; temporary-password gate (`require_user` blocks `must_change_password`); new-password rule
  (≥12 chars, not containing the username, ≥5 distinct); username/missing-account timing equalised with
  a dummy hash and a single error string (no enumeration).
- **CSRF / same-origin writes.** Evil `Origin` → 403, `Sec-Fetch-Site: cross-site` → 403, same-origin →
  201; cookie is `Secure`+`HttpOnly`+`SameSite=Strict`; CORS (when configured) is `allow_credentials=False`,
  GET/POST only (P10).
- **Two-factor / passkeys.** TOTP after the password with a ±30 s window and a per-step replay guard;
  8 one-time backup codes (now atomic); passkeys with user-verification required, origin/RP bound to
  `Host` and verified against the browser-signed origin, challenges single-use/kind-scoped/5-min,
  clone detection, failures feed the login throttle; deactivated person cannot sign in with a key.
- **Login throttle:** 10 failures / 15 min **per IP, shared across password, step-up, TOTP and passkey
  paths** (✓live: 429 after the shared count). **Single worker** by design — no `--workers` in the
  `CMD`, so the in-process throttle/replay/challenge stores are coherent.
- **Input handling.** Workbook import capped 10 MB + zip-bomb precheck + threadpool + **defusedxml
  actually engaged** (`openpyxl.xml.DEFUSEDXML == True`, confirmed) + `data_only=True`; all
  customer-supplied text (`customer_name`, `address`, supplier `brands`, inverter certs) escaped with
  `xml.sax.saxutils.escape` before ReportLab markup; download names ASCII-safe with a UTF-8 alternative.
- **Website build.** No inline `<script>` in any page (external `/static/site.js` and
  `/widget/quick.js` only); honeypot on the lead form; public process CSP/HSTS/nosniff/referrer/
  permissions headers set.
- **Logs.** The `solarapp.audit` log records logins, step-ups, lead/settings/import/deletion and
  People changes with the client address, and **no password, TOTP/backup code, cookie, secret key or
  internal token appears in either log** (scanned).
- **Containers / deployment.** Unprivileged `10001`, `read_only`, `cap_drop: [ALL]`, `no-new-privileges`,
  `pids_limit`, `mem_limit`, rotated logs, python base digest-pinned, workbook mounted `:ro` into the
  private process only, three Docker networks with `internal` cut off from the internet, host publishes
  no ports; secrets fail closed (`change-me` password refused; short/example secret key regenerated to
  `data/secret.key` at 0600); public process refuses to start without the internal token.

---

## Probe log (my servers: 8030 private, 8031 public — now stopped)

- **P1** (H1): owner login → 200; live cookie payload `{"id":1,"u":"admin","g":"0deb515bad534695"}`;
  `g` is keyed HMAC (16 hex), not `sha256(password)[:12]`.
- **P2b**: engineer `juan` after finishing setup → 403 on `GET/POST /api/users`, `PUT /api/settings`,
  `PUT /api/pricing/config`, `DELETE /api/pricing/items/*`; 200 on `/api/assessments`, `/api/leads`,
  `/api/pricing/items` (and sees `list_price`); 204 deleting his own test assessment.
- **P3** (M2): cookie-only (no password, no browser headers) → `POST /passkeys/options` **403**,
  `POST /passkeys/{id}/remove` **403**, `POST /totp/begin` **403**; with the correct password → 200.
- **P4** (L3): 1 MB body → **413**; chunked/no-length → **411**; normal → 201.
- **P5** (L5): `/estimate` → embed CSP, no `X-Frame-Options`; `/login` → office CSP + `X-Frame-Options:
  DENY`.
- **P6** (L4, accepted): anonymous `/api/auth/me` → `two_factor:false, passkeys:false` (posture only,
  gated on whether any key is registered anywhere — accepted in DECISIONS round two).
- **P7**: 10 shared failures (step-ups + logins) from one IP → **429** with `Retry-After`.
- **P8** (M3): cookie captured, password changed on another session → captured cookie **401**.
- **P9** (M3): owner deactivates a signed-in engineer → his live cookie **401** at once; still **401**
  after reactivation (generation rotated again).
- **P10**: evil `Origin` → 403; `Sec-Fetch-Site: cross-site` → 403; same-origin → 201.
- **P11**: public `/api/quick/status` → 200; private `/api/quick/*` no/wrong token → 404, right token →
  200; public blocks `/api/assessments|users|auth/login|leads|settings` → 404; public 16 KB body → 413.
- **P12**: 65 anonymous `/api/auth/passkey/options` from one IP → 60×404 then 5×429 (own per-IP limit,
  no key → 404, no over-disclosure).
- **P-CONC** (M1): 16 threads, same backup code → **1/16** accepted, 7 left; same TOTP → replay guard holds.
- **P-LOCKRACE** (finding 1): `auth_routes._lock is quick_routes._lock → False`,
  `auth_routes._hits is quick_routes._hits → True`; concurrent insert (auth lock) + sweep (quick lock)
  → **204** `dictionary changed size during iteration`.
- **Logs**: no password/code/cookie/secret/token in `private.log` or `public.log`; no 500/traceback
  during normal probing.

Scripts: `security/probe.py`, `security/probe2.py`, `security/conc.py`, `security/lockrace.py`.
