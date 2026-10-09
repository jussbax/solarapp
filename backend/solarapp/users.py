"""People, from the server (recovery and first set-up; the owner normally manages people under Settings > People).

    python -m solarapp.users list
    python -m solarapp.users create <username> --name "Full Name" --role engineer|owner
    python -m solarapp.users reset-password <username>        # prints a temporary password once
    python -m solarapp.users reset-authenticator <username>   # lost phone or key: authenticator and keys off
    python -m solarapp.users deactivate <username> | activate <username>
    python -m solarapp.users role <username> owner|engineer

Run it inside the container: docker compose exec solarapp python -m solarapp.users ...
"""
from __future__ import annotations

import argparse
import sys

from sqlmodel import Session, select

from . import passkeys, twofactor
from .auth import ROLES, bootstrap_owner, hash_password, new_generation, normalise_username, owners, temporary_password
from .config import get_settings
from .db import init_engine
from .models import User


def _user(session: Session, name: str) -> User:
    u = session.exec(select(User).where(User.username == normalise_username(name))).first()
    if u is None:
        sys.exit(f"No such person: {name}")
    return u


def main(argv: list[str] | None = None, settings=None, engine=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    c = sub.add_parser("create"); c.add_argument("username"); c.add_argument("--name", default=""); c.add_argument("--role", default="engineer", choices=ROLES)
    for name in ("reset-password", "reset-authenticator", "deactivate", "activate"):
        sub.add_parser(name).add_argument("username")
    r = sub.add_parser("role"); r.add_argument("username"); r.add_argument("role", choices=ROLES)
    args = parser.parse_args(argv)
    settings = settings or get_settings()
    engine = engine or init_engine(settings.database_path)
    with Session(engine) as session:
        bootstrap_owner(session, settings)
        if args.cmd == "list":
            for u in session.exec(select(User).order_by(User.created_at)).all():
                print(f"{u.username:20} {u.role:9} {'active' if u.active else 'off':7} auth={'on' if twofactor.enabled(u) else 'off':3} keys={len(passkeys.keys_of(session, u))}  {u.display_name}")
            return 0
        if args.cmd == "create":
            name = normalise_username(args.username)
            if session.exec(select(User).where(User.username == name)).first():
                sys.exit("That username is taken.")
            temp = temporary_password()
            session.add(User(username=name, display_name=args.name or name, role=args.role, password_hash=hash_password(temp), must_change_password=True, session_generation=new_generation()))
            session.commit()
            print(f"Created {name} ({args.role}). Temporary password, shown once: {temp}")
            print("They change it at their first sign-in.")
            return 0
        u = _user(session, args.username)
        if args.cmd == "reset-password":
            temp = temporary_password()
            u.password_hash, u.must_change_password, u.session_generation = hash_password(temp), True, new_generation()
            session.add(u); session.commit()
            print(f"Temporary password for {u.username}, shown once: {temp}")
        elif args.cmd == "reset-authenticator":
            twofactor.disable(session, u)
            n = passkeys.remove_all(session, u)
            u.session_generation = new_generation(); session.add(u); session.commit()
            print(f"Authenticator off and {n} key(s) removed for {u.username}; they sign in with the password and set them up again.")
        elif args.cmd in ("deactivate", "activate"):
            active = args.cmd == "activate"
            if not active and u.role == "owner" and len([o for o in owners(session) if o.id != u.id]) == 0:
                sys.exit("This is the only active owner. Make someone else an owner first.")
            u.active = active
            if not active:
                u.session_generation = new_generation()
            session.add(u); session.commit()
            print(f"{u.username} is now {'active' if active else 'deactivated'}.")
        elif args.cmd == "role":
            if args.role != "owner" and u.role == "owner" and u.active and len([o for o in owners(session) if o.id != u.id]) == 0:
                sys.exit("This is the only active owner. Make someone else an owner first.")
            u.role, u.session_generation = args.role, new_generation()
            session.add(u); session.commit()
            print(f"{u.username} is now {args.role}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
