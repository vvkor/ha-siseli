"""Siseli open-platform request signing for python-siseli HTTP client.

MD5 usage in this module is protocol-mandated by the upstream Siseli web client:
- MD5(app_id) is used to derive AES key/IV for secret decryption.
- MD5(HMAC-SHA256(...)) is used for request signature finalization.
This integration mirrors the remote API contract and does not introduce MD5 as a
new security primitive.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Iterable
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qsl
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .const import SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED

_OPEN_SIGNED_QUERY_KEYS = {
    "IOT-Open-AppID",
    "IOT-Open-Nonce",
    "IOT-Open-Sign",
    "IOT-Open-Body-Hash",
}


def _to_hex_utf8(text: str) -> str:
    return text.encode("utf-8").hex()


def _sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _md5_hex(raw: bytes) -> str:
    # MD5 is required by the Siseli Open signing protocol (HMAC-SHA256 output -> MD5).
    return hashlib.md5(raw, usedforsecurity=False).hexdigest()


@lru_cache(maxsize=4)
def decrypt_open_secret(app_id: str, encrypted_secret: str) -> str:
    """Decrypt encrypted Siseli app secret with CryptoJS-compatible AES-CBC/ZeroPadding."""
    # MD5(app_id) key/iv derivation is required by the official web client behavior.
    app_md5 = hashlib.md5(
        app_id.encode("utf-8"), usedforsecurity=False
    ).hexdigest().lower()
    key = app_md5[:16].encode("utf-8")
    iv = app_md5[16:].encode("utf-8")
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(base64.b64decode(encrypted_secret)) + decryptor.finalize()
    return decrypted.rstrip(b"\x00").decode("utf-8")


def build_open_signature(
    *,
    query_pairs: Iterable[tuple[str, str]],
    app_id: str,
    app_secret: str,
    nonce: str,
    body_hash: str,
) -> str:
    """Build IOT-Open-Sign value from request metadata."""
    params = [(k, v) for k, v in query_pairs if k not in _OPEN_SIGNED_QUERY_KEYS]
    params.extend(
        [
            ("IOT-Open-AppID", app_id),
            ("IOT-Open-Nonce", nonce),
            ("IOT-Open-Body-Hash", body_hash),
        ]
    )
    serialized = "&".join(f"{k}={v}" for k, v in sorted(params, key=lambda item: item[0]))
    hmac_raw = hmac.new(
        app_secret.encode("utf-8"),
        _to_hex_utf8(serialized).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return _md5_hex(hmac_raw)


def build_open_headers(
    *,
    method: str,
    query: str,
    body: bytes | None,
    app_id: str,
    app_secret: str,
    timezone: str,
    nonce: str,
) -> dict[str, str]:
    """Build per-request Siseli open-platform headers."""
    body_hash = ""
    if method.upper() != "GET":
        body_hash = _sha256_hex(body or b"")
    query_pairs = parse_qsl(query, keep_blank_values=True)
    sign = build_open_signature(
        query_pairs=query_pairs,
        app_id=app_id,
        app_secret=app_secret,
        nonce=nonce,
        body_hash=body_hash,
    )
    return {
        "IOT-Time-Zone": timezone,
        "IOT-Open-AppID": app_id,
        "IOT-Open-Nonce": nonce,
        "IOT-Open-Body-Hash": body_hash,
        "IOT-Open-Sign": sign,
    }


def attach_open_auth(client: Any) -> None:
    """Attach signed-request hook to SiseliClient's internal httpx client."""
    if not hasattr(client, "_http") or not hasattr(client._http, "event_hooks"):
        raise AttributeError(
            "SiseliClient does not expose '_http.event_hooks'; cannot attach signing hook."
        )

    try:
        if client.__dict__.get("_siseli_open_auth_attached", False):
            return
    except AttributeError:
        if getattr(client, "_siseli_open_auth_attached", False):
            return

    app_secret = decrypt_open_secret(SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED)
    timezone = getattr(client, "_timezone", "UTC")

    async def _sign_request(request: httpx.Request) -> None:
        nonce = uuid4().hex
        headers = build_open_headers(
            method=request.method,
            query=request.url.query.decode("utf-8"),
            body=request.content,
            app_id=SISELI_APP_ID,
            app_secret=app_secret,
            timezone=timezone,
            nonce=nonce,
        )
        request.headers.update(headers)

    client._http.event_hooks.setdefault("request", []).append(_sign_request)
    client._siseli_open_auth_attached = True
