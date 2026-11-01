"""Parollar we giriş tokenleri (goşmaça kitaphanasyz, diňe standart kitaphana).

Parol: PBKDF2-SHA256, her parol üçin aýratyn duz. Token: {"uid", "exp"} JSON-y + HMAC-SHA256 goly
(JWT ýaly, ýöne ýönekeý). Gizlin açar sazlamalardan ýa-da backend/.secret_key faýlyndan alynýar.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from app.core.config import settings

ITERATIONS = 200_000
_SECRET_FILE = Path(__file__).resolve().parents[2] / ".secret_key"


def _secret() -> bytes:
    if settings.secret_key:
        return settings.secret_key.encode()
    if not _SECRET_FILE.exists():
        _SECRET_FILE.write_text(secrets.token_urlsafe(48))
    return _SECRET_FILE.read_text().strip().encode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(check.hex(), digest)


def new_password(length: int = 8) -> str:
    """Wagtlaýyn parol: okamak aňsat bolar ýaly meňzeş harplar (0/O, 1/l) ýok."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(user_id: int, days: int | None = None) -> str:
    payload = _b64(json.dumps({"uid": user_id, "exp": int(time.time()) + 86400 * (days or settings.token_days)})
                   .encode())
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(token: str) -> int | None:
    """Dogry we möhleti geçmedik tokenden ulanyjy id-sini gaýtarýar, ýogsam None."""
    try:
        payload, sig = token.split(".")
        expected = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64(payload))
        return int(data["uid"]) if data["exp"] > time.time() else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
