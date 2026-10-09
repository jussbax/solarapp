"""People: the owner from .env, engineers with their own passwords, authenticators and keys, roles and recovery."""
import threading

import pyotp
import pytest
from fastapi.testclient import TestClient

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from tests.test_api import SoftKey


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("accounts")
    write_synthetic(root, (14.5, 14.75, 120.75, 121.0), 0.25)
    # an authenticator set up with the old file, and no accounts yet: both must carry over to the owner
    (root / "twofactor.json").write_text('{"secret": "JBSWY3DPEHPK3PXP", "backup": []}')
    settings = Settings(data_dir=root, app_username="Owner", app_password="owner-pass-12345", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic")
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


def _login(c: TestClient, username: str, password: str, code: str = ""):
    return c.post("/api/auth/login", json={"username": username, "password": password, "code": code})


def _owner_code(client: TestClient) -> str:
    """The owner's current code. Tests run inside one 30 s window, so the replay guard is reset first, as if a
    new window had come (the guard itself is tested on the engineer's account)."""
    from solarapp.models import User
    from sqlmodel import Session, select
    with Session(client.app.state.engine) as s:
        u = s.exec(select(User).where(User.username == "owner")).first()
        if u is not None:
            u.totp_last_step = 0
            s.add(u)
            s.commit()
    return pyotp.TOTP("JBSWY3DPEHPK3PXP").now()


def _fresh_fails():
    from solarapp.api import auth_routes
    auth_routes._fails.clear()


def test_owner_bootstraps_from_env_with_the_old_authenticator(client):
    _fresh_fails()
    r = _login(client, "owner", "owner-pass-12345")
    assert r.status_code == 401 and "code" in r.json()["detail"]          # the file's secret moved to the owner
    r = _login(client, "OWNER", "owner-pass-12345", _owner_code(client))        # usernames are case-insensitive
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["role"] == "owner" and me["two_factor"] is True and me["must_change_password"] is False and me["display_name"] == "Owner"
    assert client.get("/api/auth/me").json()["signed_in"] is True
    assert client.get("/api/assessments").status_code == 200


def test_owner_adds_an_engineer_who_changes_the_temporary_password_first(client):
    _fresh_fails()
    r = client.post("/api/users", json={"username": "Juan.Dela-Cruz", "display_name": "Juan dela Cruz", "role": "engineer"})
    assert r.status_code == 201, r.text
    temp = r.json()["temporary_password"]
    assert r.json()["username"] == "juan.dela-cruz" and r.json()["must_change_password"] is True and len(temp) >= 16
    assert client.post("/api/users", json={"username": "juan.dela-cruz", "role": "engineer"}).status_code == 409
    assert client.post("/api/users", json={"username": "bad name!", "role": "engineer"}).status_code == 422
    assert client.post("/api/users", json={"username": "x", "role": "boss"}).status_code == 422
    assert {u["username"] for u in client.get("/api/users").json()} == {"owner", "juan.dela-cruz"}
    # the engineer signs in with the temporary password but can do nothing else until it is changed
    client.post("/api/auth/logout")
    r = _login(client, "juan.dela-cruz", temp)
    assert r.status_code == 200 and r.json()["must_change_password"] is True and r.json()["role"] == "engineer"
    assert client.get("/api/assessments").status_code == 403
    assert client.get("/api/users").status_code == 403
    assert client.post("/api/auth/password", json={"current_password": temp, "new_password": "short"}).status_code == 422
    assert client.post("/api/auth/password", json={"current_password": "wrong", "new_password": "a long enough sentence"}).status_code == 403
    r = client.post("/api/auth/password", json={"current_password": temp, "new_password": "roof readings at noon"})
    assert r.status_code == 200 and r.json()["must_change_password"] is False
    assert client.get("/api/assessments").status_code == 200            # the same device stays signed in
    assert client.get("/api/auth/me").json()["username"] == "juan.dela-cruz"
    # the temporary password is dead
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", temp).status_code == 401
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 200


def test_engineer_cannot_touch_owner_only_things(client):
    _fresh_fails()
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 200
    assert client.get("/api/settings").status_code == 200                # reading is fine: documents need the profile
    assert client.put("/api/settings", json={"phone": "1"}).status_code == 403
    assert client.get("/api/pricing/config").status_code == 200
    assert client.put("/api/pricing/config", json={}).status_code == 403
    assert client.post("/api/pricing/config/reset").status_code == 403
    assert client.delete("/api/pricing/items/BC-PNL-001").status_code == 403
    assert client.get("/api/users").status_code == 403
    assert client.post("/api/users", json={"username": "x", "role": "engineer"}).status_code == 403
    assert client.get("/api/leads").status_code == 403                  # the booking inbox is the owner's (the CRM's)
    assert client.get("/api/leads/open").status_code == 200             # the hand-off list is everyone's


def test_engineer_sets_up_an_authenticator_in_the_browser(client):
    _fresh_fails()
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 200
    assert client.post("/api/auth/totp/begin", json={"password": "nope"}).status_code == 403
    r = client.post("/api/auth/totp/begin", json={"password": "roof readings at noon"})
    assert r.status_code == 200 and r.json()["qr"].startswith("data:image/png;base64,") and "otpauth://totp/" in r.json()["uri"]
    secret = r.json()["secret"]
    # not on until confirmed: the password alone still signs in
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 200
    assert client.post("/api/auth/totp/confirm", json={"code": "000000"}).status_code == 422
    r = client.post("/api/auth/totp/confirm", json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200 and len(r.json()["backup_codes"]) == 8
    codes = r.json()["backup_codes"]
    assert client.get("/api/auth/me").json()["two_factor"] is True
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 401
    # the current code already confirmed the set-up: that window is spent, so a backup code gets in now
    assert _login(client, "juan.dela-cruz", "roof readings at noon", codes[0]).status_code == 200
    assert client.get("/api/auth/me").json()["backup_codes_left"] == 7
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", "roof readings at noon", codes[0]).status_code == 401   # one use only
    # a backup code is consumed exactly once even under concurrent sign-ins
    from solarapp import twofactor
    from solarapp.models import User
    from sqlmodel import Session, select
    results = []
    barrier = threading.Barrier(10)

    def attempt():
        with Session(client.app.state.engine) as s:
            u = s.exec(select(User).where(User.username == "juan.dela-cruz")).first()
            barrier.wait()
            results.append(twofactor.verify(s, u, codes[1]))

    threads = [threading.Thread(target=attempt) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1
    # turning it off needs the password and a fresh code
    assert _login(client, "juan.dela-cruz", "roof readings at noon", codes[2]).status_code == 200
    assert client.post("/api/auth/totp/disable", json={"password": "roof readings at noon", "code": "000000"}).status_code == 403
    assert client.post("/api/auth/totp/disable", json={"password": "roof readings at noon", "code": codes[3]}).status_code == 200
    assert client.get("/api/auth/me").json()["two_factor"] is False


def test_keys_belong_to_their_person(client):
    _fresh_fails()
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 200
    key = SoftKey("testserver", "http://testserver")
    opts = client.post("/api/auth/passkeys/options", json={"password": "roof readings at noon"}).json()
    assert opts["options"]["user"]["name"] == "juan.dela-cruz"
    # the challenge stands in for the password on the second call: it was issued after the step-up, to Juan only
    r = client.post("/api/auth/passkeys", json={"challenge_id": opts["challenge_id"], "name": "Juan's key", "credential": key.register(opts["options"])})
    assert r.status_code == 201, r.text
    key_id = r.json()["id"]
    assert [k["name"] for k in client.get("/api/auth/passkeys").json()] == ["Juan's key"]
    # the key alone signs Juan in, as Juan
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json()["passkeys"] is True
    opts = client.post("/api/auth/passkey/options").json()
    r = client.post("/api/auth/passkey/login", json={"challenge_id": opts["challenge_id"], "credential": key.sign(opts["options"])})
    assert r.status_code == 200 and r.json()["username"] == "juan.dela-cruz" and r.json()["role"] == "engineer"
    # the owner sees no key of Juan's under their own account and cannot remove it from there
    client.post("/api/auth/logout")
    assert _login(client, "owner", "owner-pass-12345", _owner_code(client)).status_code == 200
    assert client.get("/api/auth/passkeys").json() == []
    assert client.post(f"/api/auth/passkeys/{key_id}/remove", json={"password": "owner-pass-12345", "code": _owner_code(client)}).status_code in (403, 404)
    # a registration challenge issued to the owner cannot be redeemed by anyone else
    opts = client.post("/api/auth/passkeys/options", json={"password": "owner-pass-12345", "code": _owner_code(client)}).json()
    client.post("/api/auth/logout")
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 200
    other = SoftKey("testserver", "http://testserver")
    r = client.post("/api/auth/passkeys", json={"challenge_id": opts["challenge_id"], "name": "stolen", "credential": other.register(opts["options"])})
    assert r.status_code == 400 and "expired" in r.json()["detail"]
    # and no challenge at all, or one already spent, is refused
    assert client.post("/api/auth/passkeys", json={"challenge_id": "nope", "name": "x", "credential": other.register(opts["options"])}).status_code == 400


def test_with_the_authenticator_on_adding_a_key_spends_one_code(client):
    """The owner has the authenticator on: one 6-digit code (already used at sign-in) must not be asked twice."""
    _fresh_fails()
    client.post("/api/auth/logout")
    assert _login(client, "owner", "owner-pass-12345", _owner_code(client)).status_code == 200
    key = SoftKey("testserver", "http://testserver")
    code = _owner_code(client)
    opts = client.post("/api/auth/passkeys/options", json={"password": "owner-pass-12345", "code": code})
    assert opts.status_code == 200, opts.text
    opts = opts.json()
    # the same code again would be a replay; the registration needs none
    assert client.post("/api/auth/passkeys/options", json={"password": "owner-pass-12345", "code": code}).status_code == 403
    r = client.post("/api/auth/passkeys", json={"challenge_id": opts["challenge_id"], "name": "Owner key", "credential": key.register(opts["options"])})
    assert r.status_code == 201, r.text
    assert client.post(f"/api/auth/passkeys/{r.json()['id']}/remove", json={"password": "owner-pass-12345", "code": _owner_code(client)}).status_code == 204


def test_deactivation_and_resets_end_sessions_and_keep_one_owner(client):
    _fresh_fails()
    client.post("/api/auth/logout")
    owner = TestClient(client.app)
    assert _login(owner, "owner", "owner-pass-12345", _owner_code(client)).status_code == 200
    juan_id = next(u["id"] for u in owner.get("/api/users").json() if u["username"] == "juan.dela-cruz")
    owner_id = next(u["id"] for u in owner.get("/api/users").json() if u["username"] == "owner")
    # Juan is signed in on another device
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 200
    assert client.get("/api/assessments").status_code == 200
    # a reset by the owner ends Juan's session and gives a temporary password
    r = owner.post(f"/api/users/{juan_id}/reset-authenticator")
    assert r.status_code == 200 and r.json()["passkeys"] == 0 and r.json()["two_factor"] is False
    assert client.get("/api/assessments").status_code == 401
    r = owner.post(f"/api/users/{juan_id}/reset-password")
    temp = r.json()["temporary_password"]
    assert _login(client, "juan.dela-cruz", "roof readings at noon").status_code == 401
    assert _login(client, "juan.dela-cruz", temp).status_code == 200 and client.get("/api/auth/me").json()["must_change_password"] is True
    # deactivated: no sign-in at all, and the live session is gone
    assert owner.patch(f"/api/users/{juan_id}", json={"active": False}).status_code == 200
    assert client.get("/api/auth/me").json()["signed_in"] is False
    assert _login(client, "juan.dela-cruz", temp).status_code == 401
    assert owner.patch(f"/api/users/{juan_id}", json={"active": True}).status_code == 200
    # the only owner cannot demote or deactivate themselves, and the last owner is protected
    assert owner.patch(f"/api/users/{owner_id}", json={"role": "engineer"}).status_code == 409
    assert owner.patch(f"/api/users/{owner_id}", json={"active": False}).status_code == 409
    assert owner.patch(f"/api/users/{juan_id}", json={"role": "owner"}).status_code == 200
    assert owner.patch(f"/api/users/{juan_id}", json={"role": "engineer", "display_name": "Juan"}).status_code == 200
    # sign out everywhere ends every session of that person only
    assert _login(client, "juan.dela-cruz", temp).status_code == 200
    assert owner.post("/api/auth/signout-everywhere").status_code == 200
    assert owner.get("/api/auth/me").json()["signed_in"] is False
    assert client.get("/api/auth/me").json()["signed_in"] is True


def test_cookie_carries_no_password_material_and_a_stale_cookie_is_refused(client):
    import base64
    import json
    from solarapp.auth import COOKIE
    _fresh_fails()
    client.post("/api/auth/logout")
    assert _login(client, "owner", "owner-pass-12345", _owner_code(client)).status_code == 200
    payload = client.cookies[COOKIE].split(".")[0]
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert set(data) == {"id", "u", "g"} and len(data["g"]) == 16 and "owner-pass" not in client.cookies[COOKIE]
    # the owner changes their password: the cookie on this device is renewed, the old one is dead elsewhere
    old = client.cookies[COOKIE]
    r = client.post("/api/auth/password", json={"current_password": "owner-pass-12345", "code": _owner_code(client), "new_password": "a sunny day in Pila 2026"})
    assert r.status_code == 200
    assert client.get("/api/auth/me").json()["signed_in"] is True
    assert not client.get("/api/auth/me", cookies={COOKIE: old}).json()["signed_in"]
    # and .env's password no longer opens the door: it was only the bootstrap
    client.post("/api/auth/logout")
    assert _login(client, "owner", "owner-pass-12345", _owner_code(client)).status_code == 401


def test_blank_env_password_means_no_bootstrap_and_the_cli_makes_the_owner(tmp_path, capsys):
    """Once an owner exists the .env password may be cleared; with no accounts at all, the CLI creates the first owner."""
    from solarapp.users import main as users_main

    root = tmp_path / "data"
    write_synthetic(root, (14.5, 14.75, 120.75, 121.0), 0.25)
    settings = Settings(data_dir=root, app_username="admin", app_password="", secret_key="k" * 40, cookie_secure=False, static_dir=root / "nostatic")
    with TestClient(create_app(settings)) as c:
        assert _login(c, "admin", "").status_code == 401
        assert _login(c, "admin", "anything-at-all-12").status_code == 401
        assert users_main(["create", "maria", "--name", "Maria", "--role", "owner"], settings=settings, engine=c.app.state.engine) == 0
        temp = capsys.readouterr().out.split("shown once: ")[1].split()[0]
        r = _login(c, "maria", temp)
        assert r.status_code == 200 and r.json()["role"] == "owner" and r.json()["must_change_password"] is True


def test_cli_creates_and_recovers_people(client, capsys):
    from solarapp import users as cli_module
    from solarapp.config import get_settings

    class cli:
        @staticmethod
        def main(argv):
            return cli_module.main(argv, settings=client.app.dependency_overrides[get_settings](), engine=client.app.state.engine)

    assert cli.main(["create", "maria", "--name", "Maria Santos", "--role", "engineer"]) == 0
    out = capsys.readouterr().out
    assert "Temporary password" in out
    temp = out.split(":")[-1].strip().split()[0]
    assert cli.main(["list"]) == 0 and "maria" in capsys.readouterr().out
    _fresh_fails()
    client.post("/api/auth/logout")
    assert _login(client, "maria", temp).status_code == 200
    assert cli.main(["deactivate", "maria"]) == 0
    assert client.get("/api/auth/me").json()["signed_in"] is False
    assert cli.main(["activate", "maria"]) == 0 and cli.main(["reset-password", "maria"]) == 0
    with pytest.raises(SystemExit):
        cli.main(["deactivate", "owner"])   # the only active owner
