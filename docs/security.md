# Security: what the app does, and what the server and Cloudflare must do

The app side is in the code (see DECISIONS.md, "Security"). This page is the
owner's side: settings on Cloudflare, the server, backups and the Data
Privacy Act routine. Do them in this order.

## Two-factor login for the back office (do this first)

The back office asks for a code from an authenticator app (Google
Authenticator, Authy, Microsoft Authenticator) after the password. Codes
work offline, so the login works on a roof with no signal. Set it up once:

```
docker compose exec solarapp python -m solarapp.twofactor setup
```

Scan the QR code it prints (it is also saved as `data/twofactor-qr.png`;
delete that file after scanning) and write down the eight backup codes
somewhere safe, away from the phone. Each backup code opens the door once
if the phone is lost. `status` shows how many are left; `setup` again
replaces the secret and the codes; `disable` switches it off. The secret
lives in `data/twofactor.json`, never in `.env`.

With this in place, Cloudflare Access (below) is an optional extra layer,
not the only lock.

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
  (add `--dry-run` to see what it would do). Leads that never became a
  visit lose their name, contact, address and precise pin after 12 months;
  estimate rows older than 90 days are deleted. Add it to cron on the 1st.
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

## What to read in the logs

`docker compose logs --since 24h solarapp | grep solarapp.audit` shows
logins (ok, failed, throttled), leads created, settings changes, imports
and deletions, each with the client address. A rejected authenticator
code is logged as `login code rejected`. If you also use Cloudflare
Access, it keeps the outer login trail.
