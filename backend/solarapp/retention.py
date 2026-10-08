"""Data retention: anonymise stale leads and trim the estimate log, as the privacy notice promises.

    python -m solarapp.retention            # apply
    python -m solarapp.retention --dry-run  # only report

Leads that never became a visit (stage lead or contacted) older than
--lead-months lose their name, contact, address and pin; the row stays so
the funnel counts hold. Estimate log rows older than --estimate-days are
deleted. Run it monthly from cron (see README).
"""
from __future__ import annotations

import argparse
import copy
import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from .config import get_settings
from .db import init_engine
from .models import Assessment, QuickEstimateLog

log = logging.getLogger("solarapp.audit")


def run(session: Session, lead_months: int = 12, estimate_days: int = 90, dry_run: bool = False, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    lead_cutoff = now - timedelta(days=30 * lead_months)
    est_cutoff = now - timedelta(days=estimate_days)
    anonymised = 0
    for a in session.exec(select(Assessment).where(Assessment.updated_at < lead_cutoff)).all():
        doc = copy.deepcopy(a.doc or {})  # a new object, so the JSON column is seen as changed
        stage = (doc.get("program") or {}).get("stage", "assessed")
        if stage not in ("lead", "contacted") or doc.get("anonymised"):
            continue
        anonymised += 1
        if dry_run:
            continue
        doc["customer_name"] = ""
        doc["address"] = ""
        doc["notes"] = "Lead anonymised under the retention schedule."
        doc["lat"] = round(doc["lat"], 2) if isinstance(doc.get("lat"), (int, float)) else None
        doc["lon"] = round(doc["lon"], 2) if isinstance(doc.get("lon"), (int, float)) else None
        if doc.get("lead"):
            doc["lead"] = {**doc["lead"], "contact": "", "town": doc["lead"].get("town", ""), "source": doc["lead"].get("source", {})}
        doc["anonymised"] = True
        a.doc = doc
        a.customer_name = ""
        a.address = ""
        session.add(a)
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
    parser.add_argument("--lead-months", type=int, default=12)
    parser.add_argument("--estimate-days", type=int, default=90)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    settings = get_settings()
    engine = init_engine(settings.database_path)
    with Session(engine) as session:
        result = run(session, args.lead_months, args.estimate_days, args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
