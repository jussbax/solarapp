# Security: what the app does, and what the server and Cloudflare must do

The app side is in the code (see DECISIONS.md, "Security"). This page is the
owner's side: settings on Cloudflare, the server, backups and the Data
Privacy Act routine. Do them in this order.

## Accounts: who can sign in (do this first)

Everyone who opens the back office has their own username and password.
Two roles: the **owner** manages people, the company profile, pricing
settings and the materials list; an **engineer** works on leads, projects
and every engineering output. The server enforces the split, not only the
screens.

The username and password in `.env` are used once, at the first start, to
create the owner's account. From then on passwords live in the database
(as argon2 hashes), and the `.env` password may be cleared. An
authenticator set up the old way (the `twofactor.json` file) and any
security keys registered before accounts existed carry over to the owner.

Give an engineer access under Settings › People: username, name, role,
Add. A temporary password is shown once; pass it on in person or by a call,
never in the same message as the address. It opens nothing: at the first
sign-in the person must choose their own password (twelve characters or
more, not containing their username). The same card resets a password or
an authenticator, changes a role, and deactivates a person, which ends
their sessions at once.

## Two-factor login: the authenticator app

Each person turns it on for themselves under Settings › Your account:
enter the password under "Confirm it's you", press "Set up the
authenticator app", scan the QR code with Google Authenticator, Microsoft
Authenticator, Aegis or 1Password (or type the key shown), enter the
6-digit code, and write down the eight backup codes shown once. From then
on the login asks for the code after the password. Codes work offline, so
the login works on a roof with no signal; each backup code opens the door
once if the phone is lost.

The owner should turn it on first, and ask every engineer to do the same
before they work from outside the office. With this in place, Cloudflare
Access (below) is an optional extra layer, not the only lock.

## Security keys and passkeys

A hardware key (YubiKey or similar) or a passkey on your phone signs you in
with one touch: no password, no code. The key proves possession and its PIN
or fingerprint proves it is you, so it counts as both factors, and the
browser only releases a signature for the exact hostname the key was
registered on, so a look-alike site gets nothing. Keys belong to the person
who added them.

1. Open Settings › Your account, enter the password (and a fresh code)
   under "Confirm it's you", name the key and press "Add a security key".
   The browser asks for the key's PIN (a new key asks you to set one) and
   a touch.
2. Register a second key and keep it somewhere safe, or keep the backup
   codes: a lost key is removed from the same list, and the password with
   the code still works.
3. Passkeys need https and a real hostname. They work on
   `solar.pldevinc.com` through the tunnel and on `localhost`, not on an IP
   address on the office network.

Wrong or unknown keys count toward the same login throttle, and every
sign-in names its person and method (`method=password` or
`method=passkey`) in the audit log. Adding or removing a key, turning the
authenticator on or off and changing the password all ask for the password
(and a fresh code) again, so a stolen session cookie alone cannot do any of
it; a wrong answer counts as a failed login.

## If a phone or laptop is lost

1. Open Settings › Your account on another device and press "Sign out
   everywhere". Every session of yours ends at once, including the one on
   the lost device; sign in again afterwards.
2. Check the list of security keys and remove any you do not recognize.
   Signing out does not remove keys.
3. Change your password there too if the lost device could have had it
   saved; that also ends every other session.
4. Lost the phone with the authenticator and the backup codes? The owner
   presses "Reset authenticator" for you under People: the authenticator
   and every key of yours are removed, your sessions end, and you sign in
   with the password alone and set them up again. The owner's own
   recovery, when no owner can sign in, is on the server:
   `docker compose exec solarapp python -m solarapp.users reset-authenticator <username>`
   (or `reset-password`, `list`, `create ... --role owner`).
5. Read the audit log: an unexpected `passkey added`, `user created` or
   `password reset` line is a takeover signal.

## Cloudflare (both hostnames)

1. Account: turn on two-factor authentication. The account controls DNS,
   Access and both tunnels.
2. SSL/TLS: Always Use HTTPS, HSTS on, minimum TLS 1.2.
3. Security: the free managed WAF ruleset and Bot Fight Mode on both
   hostnames.
4. Rate limiting rules: `pldevinc.com` path starts with `/api/quick/`, 30
   requests per minute per IP, block for 10 minutes; `solar.pldevinc.com`
   path equals `/api/auth/login`, 10 per minute per IP.
5. Redirect rule: `www.pldevinc.com/*` to `https://pldevinc.com/$1`, so one
   hostname carries the visitor tokens and the ads.
6. Access (optional, a second lock in front of the app's own two-factor
   login): Zero Trust › Access › Applications › add a self-hosted
   application for `solar.pldevinc.com`, policy "allow" with your e-mail
   via one-time PIN, session 24 hours, no bypass paths. The website on
   `pldevinc.com` needs no Access rule.

## The server (Ubuntu)

1. Updates: `sudo apt update && sudo apt full-upgrade`, then
   `sudo apt install unattended-upgrades needrestart` and enable automatic
   reboots at night in `/etc/apt/apt.conf.d/50unattended-upgrades`.
2. Accounts: one non-root admin in `sudo` and `docker` (the docker group is
   root-equivalent; keep it to that one account), `sudo passwd -l root`.
3. SSH: keys only (`PasswordAuthentication no`, `PermitRootLogin no`,
   `AllowUsers <admin>`), `sudo apt install fail2ban`. Never port-forward
   SSH on the router; if you need it from outside, publish it through a
   third tunnel hostname behind Access.
4. Firewall: `sudo ufw default deny incoming; sudo ufw default allow outgoing;
   sudo ufw allow from <office LAN>/24 to any port 22; sudo ufw enable`. The
   app needs no inbound rule: the tunnels dial out. Docker bypasses ufw for
   published ports, so publish none (the default compose file publishes
   none) and set `"ip": "127.0.0.1"` in `/etc/docker/daemon.json`.
5. Docker daemon, `/etc/docker/daemon.json`:
   `{"ip":"127.0.0.1","log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"5"},"no-new-privileges":true,"live-restore":true}`.
   `chmod 600 .env`. Data volume owned by the app user: `sudo chown -R 10001:10001 data`.
6. Monthly: `docker compose build --pull && docker compose --profile tunnels up -d`,
   then `docker image prune -f`. Bump the `cloudflare/cloudflared` tag and
   the `python:3.13-slim` digest in the compose file and Dockerfile when a
   newer one exists. Check `pip-audit -r backend/requirements.lock` and
   `npm audit --omit=dev` in `frontend/`.
7. Old tunnel: once the containers carry both hostnames,
   `sudo systemctl disable --now cloudflared`, delete the old tunnel in the
   dashboard, and `sudo shred -u /etc/cloudflared/*.json`.

## Backups

Nightly at 02:00 (`crontab -e` as the admin user):

```
0 2 * * * cd /home/<admin>/solarapp && mkdir -p data/backup && docker compose exec -T solarapp python -c "import sqlite3,datetime; s=sqlite3.connect('/app/data/solarapp.db'); d=sqlite3.connect(f'/app/data/backup/solarapp-{datetime.date.today()}.db'); s.backup(d); d.close()" && find data/backup -name 'solarapp-*.db' -mtime +14 -delete && restic backup data/backup .env
```

`restic` to an off-site bucket (Backblaze B2 or Cloudflare R2) encrypts
before upload; keep the restic password and the tunnel tokens in your
password manager, not on the box. Weekly
`restic forget --keep-daily 30 --keep-monthly 12 --prune`, monthly
`restic check`, and one practised restore every quarter. The weather
dataset is re-downloadable and need not be backed up. Never copy the live
`solarapp.db` file directly; use the `.backup` command above.

## Data Privacy Act routine

- Monthly, after the backup: `docker compose exec -T solarapp python -m solarapp.retention`
  (add `--dry-run` to see what it would do). Website bookings that never
  became a project lose their name, contact, address and precise pin after
  12 months; projects are never touched; estimate rows older than 90 days
  are deleted. Add it to cron on the 1st.
- You are the Data Protection Officer; the privacy page names the owner
  from Settings. A request to see or delete someone's details: find them on
  the job list, delete the record, and delete the lead e-mail in your
  mailbox. The deletion is logged. Backups age out within 30 days.
- If data leaks (a lost laptop that was signed in, a stolen server), the
  law expects notification to the National Privacy Commission and to the
  people affected within 72 hours when the leak could enable fraud. Keep
  this page and the NPC breach form handy.
- Two-factor authentication on the mailbox that receives lead notices and
  on the Messenger account that sends the documents.

## One worker, tunnel only

Run one app worker, as the shipped command does. Do not add `--workers N`
to uvicorn: the login throttle, the authenticator replay guard and the
passkey challenge store live in the process, and several processes would
not share them.

The origin must be reachable only through the two Cloudflare tunnels. Never
publish ports on the server or expose its address: the estimate's per-visitor
rate limit and the audit log trust the visitor address the tunnel sends, and
a directly reachable origin would let anyone forge it. The Cloudflare rate
limit on `/api/quick/` is the real outer limiter.

## What to read in the logs

`docker compose logs --since 24h solarapp | grep solarapp.audit` shows
logins (ok, failed, throttled), leads created, settings changes, imports
and deletions, each with the client address. A rejected authenticator
code is logged as `login code rejected`; `step-up failed` is a wrong
password given when adding or removing a key; `sign-out everywhere` is
the owner ending every session. If you also use Cloudflare
Access, it keeps the outer login trail.
