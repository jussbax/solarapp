"""Data retention: anonymise stale leads and trim the estimate log, as the privacy notice promises.

    python -m solarapp.retention            # apply
    python -m solarapp.retention --dry-run  # only report

Bookings that never became a project (any status but converted)
and were last touched more than --lead-months ago lose their name, contact,
address, preferred time and pin; the row stays with its town, source and
the estimate they saw, so the funnel counts hold. Projects are never
anonymised: a customer's record is kept as long as the job is. Estimate log
rows older than --estimate-days are deleted. Run it monthly from cron (see
README).
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from .config import get_settings
from .db import init_engine
from .models import Lead, QuickEstimateLog

log = logging.getLogger("solarapp.audit")

ANONYMISED_NOTE = "Lead anonymised under the retention schedule."


def run(session: Session, lead_months: int = 12, estimate_days: int = 90, dry_run: bool = False, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    lead_cutoff = now - timedelta(days=30 * lead_months)
    est_cutoff = now - timedelta(days=estimate_days)
    anonymised = 0
    stale = session.exec(select(Lead).where(Lead.updated_at < lead_cutoff, Lead.status != "converted", Lead.anonymised_at.is_(None))).all()  # type: ignore[union-attr]
    for lead in stale:
        anonymised += 1
        if dry_run:
            continue
        lead.name = ""
        lead.contact = ""
        lead.address = ""
        lead.preferred_time = ""
        lead.notes = ANONYMISED_NOTE
        # a town, not a house: the pin is kept to the estimate log's precision
        lead.lat = round(lead.lat, 2) if isinstance(lead.lat, (int, float)) else None
        lead.lon = round(lead.lon, 2) if isinstance(lead.lon, (int, float)) else None
        lead.anonymised_at = now
        session.add(lead)
    old_estimates = session.exec(select(QuickEstimateLog).where(QuickEstimateLog.created_at < est_cutoff)).all()
    deleted = len(old_estimates)
    if not dry_run:
        for row in old_estimates:
            session.delete(row)
        session.commit()
        log.info("retention: anonymised %s leads older than %s months, deleted %s estimate rows older than %s days", anonymised, lead_months, deleted, estimate_days)
    return {"anonymised_leads": anonymised, "deleted_estimates": deleted, "dry_run": dry_run}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lead-months", type=int, default=12, help="anonymise inbox leads that never became a project after this many months (default 12)")
    parser.add_argument("--estimate-days", type=int, default=90, help="delete estimate log rows older than this many days (default 90)")
    parser.add_argument("--dry-run", action="store_true", help="only report the counts; change nothing")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    settings = get_settings()
    engine = init_engine(settings.database_path)
    with Session(engine) as session:
        result = run(session, args.lead_months, args.estimate_days, args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
