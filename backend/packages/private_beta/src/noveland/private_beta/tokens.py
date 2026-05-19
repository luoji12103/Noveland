from __future__ import annotations

import hashlib
import secrets


def generate_invite_token() -> str:
    return secrets.token_urlsafe(48)


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_fingerprint(token: str) -> str:
    return hash_invite_token(token)[:12]
