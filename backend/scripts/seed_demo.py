"""Create or reset the synthetic demo cohort.

    PADHOTEC_DATABASE_URL=sqlite:///./demo.db uv run python scripts/seed_demo.py --yes
    uv run python scripts/seed_demo.py --reset --yes     # replaces demo accounts, never touches real ones

Demo accounts are marked, hold invented data, and never mix with real students' statistics. The command shows
which database it will write to and asks first, because the default is the local development database.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.services.demo_data import DEMO_DOMAIN, DEMO_PASSWORD, delete_demo_accounts, has_demo_accounts, seed_demo  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="delete existing demo accounts first (real accounts are untouched)")
    ap.add_argument("--remove", action="store_true", help="delete demo accounts and stop")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = ap.parse_args()

    print(f"Database: {settings.database_url}")
    if not args.yes and input("Write demo accounts to this database? [y/N] ").strip().lower() != "y":
        sys.exit("Cancelled. Nothing was changed.")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        if args.remove:
            print(f"Removed {delete_demo_accounts(db)} demo accounts.")
            return
        if has_demo_accounts(db) and not args.reset:
            print("Demo accounts already exist. Use --reset to replace them.")
            return
        created = seed_demo(db, seed=args.seed, reset=args.reset)
    print(f"Created {len(created)} synthetic demo students.\n")
    print("Sign in with any of these (password for all: " + DEMO_PASSWORD + "):")
    for key, what in (("steady", "studies steadily, has results, a full dashboard"),
                      ("quiet", "was active, then stopped three weeks ago: shows an elevated risk"),
                      ("new", "joined six days ago: shows the cold-start messages")):
        print(f"  {key}@{DEMO_DOMAIN:<28s} {what}")


if __name__ == "__main__":
    main()
