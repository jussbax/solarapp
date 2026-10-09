"""People who may sign in, managed by the owner: add, change role, deactivate, reset a password or an authenticator."""
from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from .. import passkeys, twofactor
from ..auth import ROLES, hash_password, new_generation, normalise_username, owners, require_owner, temporary_password
from ..db import get_session
from ..models import User
from ..schemas import UserCreateIn, UserPatchIn
from .quick_routes import client_ip

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_owner)])
log = logging.getLogger("solarapp.audit")
USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{1,39}$")


def _out(u: User, session: Session) -> dict:
    return {
        "id": u.id, "username": u.username, "display_name": u.display_name or u.username, "role": u.role, "active": u.active,
        "must_change_password": u.must_change_password, "two_factor": twofactor.enabled(u), "passkeys": len(passkeys.keys_of(session, u)),
        "created_at": u.created_at.isoformat() if u.created_at else None, "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    }


def _get(session: Session, user_id: int) -> User:
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="No such person")
    return u


def _last_owner_guard(session: Session, u: User, becoming_role: str, becoming_active: bool) -> None:
    """The company must keep at least one active owner, or nobody could manage people or settings."""
    if u.role == "owner" and u.active and (becoming_role != "owner" or not becoming_active):
        if len([o for o in owners(session) if o.id != u.id]) == 0:
            raise HTTPException(status_code=409, detail="This is the only active owner. Make someone else an owner first.")


@router.get("")
def list_users(session: Session = Depends(get_session)) -> list[dict]:
    return [_out(u, session) for u in session.exec(select(User).order_by(User.created_at)).all()]


@router.post("", status_code=201)
def create_user(body: UserCreateIn, request: Request, me: User = Depends(require_owner), session: Session = Depends(get_session)) -> dict:
    """A new person gets a temporary password, shown once here; they change it at their first sign-in."""
    name = normalise_username(body.username)
    if not USERNAME.match(name):
        raise HTTPException(status_code=422, detail="Username: 2 to 40 lower-case letters, digits, dots, dashes or underscores.")
    if body.role not in ROLES:
        raise HTTPException(status_code=422, detail="Role must be owner or engineer.")
    if session.exec(select(User).where(User.username == name)).first():
        raise HTTPException(status_code=409, detail="That username is taken.")
    temp = temporary_password()
    u = User(username=name, display_name=body.display_name.strip() or name, role=body.role, password_hash=hash_password(temp),
             must_change_password=True, session_generation=new_generation())
    session.add(u)
    session.commit()
    session.refresh(u)
    log.info("user created ip=%s by=%s user=%s role=%s", client_ip(request), me.username, u.username, u.role)
    return {**_out(u, session), "temporary_password": temp}


@router.patch("/{user_id}")
def patch_user(user_id: int, body: UserPatchIn, request: Request, me: User = Depends(require_owner), session: Session = Depends(get_session)) -> dict:
    u = _get(session, user_id)
    role = body.role if body.role is not None else u.role
    active = body.active if body.active is not None else u.active
    if role not in ROLES:
        raise HTTPException(status_code=422, detail="Role must be owner or engineer.")
    if u.id == me.id and (not active or role != "owner"):
        raise HTTPException(status_code=409, detail="You cannot deactivate or demote yourself; ask another owner.")
    _last_owner_guard(session, u, role, active)
    changes = []
    if body.display_name is not None and body.display_name.strip() != u.display_name:
        u.display_name = body.display_name.strip()
        changes.append("name")
    if role != u.role:
        u.role = role
        u.session_generation = new_generation()   # a role change takes effect everywhere at once
        changes.append(f"role={role}")
    if active != u.active:
        u.active = active
        if not active:
            u.session_generation = new_generation()   # every session of a deactivated person ends now
        changes.append("active" if active else "deactivated")
    session.add(u)
    session.commit()
    session.refresh(u)
    if changes:
        log.warning("user changed ip=%s by=%s user=%s %s", client_ip(request), me.username, u.username, ", ".join(changes))
    return _out(u, session)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, request: Request, me: User = Depends(require_owner), session: Session = Depends(get_session)) -> dict:
    """A new temporary password, shown once; the person's other sessions end and they must change it at sign-in."""
    u = _get(session, user_id)
    temp = temporary_password()
    u.password_hash = hash_password(temp)
    u.must_change_password = True
    u.session_generation = new_generation()
    session.add(u)
    session.commit()
    session.refresh(u)
    log.warning("password reset ip=%s by=%s user=%s", client_ip(request), me.username, u.username)
    return {**_out(u, session), "temporary_password": temp}


@router.post("/{user_id}/reset-authenticator")
def reset_authenticator(user_id: int, request: Request, me: User = Depends(require_owner), session: Session = Depends(get_session)) -> dict:
    """A lost phone or key: the authenticator and every security key of the person are removed, and their
    sessions end, so they sign in with the password alone and set them up again."""
    u = _get(session, user_id)
    twofactor.disable(session, u)
    removed = passkeys.remove_all(session, u)
    u.session_generation = new_generation()
    session.add(u)
    session.commit()
    session.refresh(u)
    log.warning("authenticator and %s key(s) reset ip=%s by=%s user=%s", removed, client_ip(request), me.username, u.username)
    return _out(u, session)
