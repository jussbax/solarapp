"""python -m solarapp.pricing <workbook.xlsx> [--keep-config]  -> import into the app database."""
import argparse
import sys

from ..config import get_settings
from ..db import init_engine
from sqlmodel import Session

from .store import import_workbook


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook")
    ap.add_argument("--keep-config", action="store_true", help="update items and suppliers only; keep the app's pricing settings")
    args = ap.parse_args(argv)
    settings = get_settings()
    engine = init_engine(settings.database_path)
    with Session(engine) as session:
        r = import_workbook(session, args.workbook, replace_config=not args.keep_config)
    print(f"added {r['added']}, updated {r['updated']}, suppliers {r['suppliers']}")
    for w in r["warnings"]:
        print("warning:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
