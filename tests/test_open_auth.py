"""Tests for Siseli Open API signing helpers."""

from __future__ import annotations

import hashlib

import httpx

from siseli.const import SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED
from siseli.open_auth import (
    _sha256_hex,
    attach_open_auth,
    build_open_headers,
    decrypt_open_secret,
)


class _MockHttpClient:
    def __init__(self) -> None:
        self.event_hooks = {"request": []}


class _MockSiseliClient:
    _timezone = "Europe/Moscow"

    def __init__(self) -> None:
        self._http = _MockHttpClient()


def test_decrypt_open_secret_with_app_id() -> None:
    """Encrypted Open secret is decrypted with AppID-derived key/IV."""
    assert (
        decrypt_open_secret(SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED)
        == "CJbrtLtqFES62bJ3ZW7c"
    )


def test_get_request_signing_uses_empty_body_hash() -> None:
    """GET requests must sign with an empty body hash."""
    secret = decrypt_open_secret(SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED)
    headers = build_open_headers(
        method="GET",
        query="b=2&a=1",
        body=None,
        app_id=SISELI_APP_ID,
        app_secret=secret,
        timezone="UTC",
        nonce="nonce-123",
    )
    assert headers["IOT-Open-Body-Hash"] == ""
    assert headers["IOT-Open-Sign"] == "bee1c1c32629baf72be698fbe53fdc11"


def test_post_request_signing_with_json_body() -> None:
    """POST requests must hash and sign the raw JSON body bytes."""
    secret = decrypt_open_secret(SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED)
    body = b'{"name":"abc","value":123}'
    headers = build_open_headers(
        method="POST",
        query="z=9",
        body=body,
        app_id=SISELI_APP_ID,
        app_secret=secret,
        timezone="UTC",
        nonce="nonce-123",
    )
    assert headers["IOT-Open-Body-Hash"] == hashlib.sha256(body).hexdigest()
    assert headers["IOT-Open-Sign"] == "1f3525cce7ea5fa378409070c17f0076"


def test_unicode_json_body_signing() -> None:
    """Unicode body content must be hashed/signatured as UTF-8 bytes."""
    secret = decrypt_open_secret(SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED)
    body = '{"text":"Привет 🌞"}'.encode()
    headers = build_open_headers(
        method="POST",
        query="",
        body=body,
        app_id=SISELI_APP_ID,
        app_secret=secret,
        timezone="UTC",
        nonce="nonce-123",
    )
    assert headers["IOT-Open-Body-Hash"] == hashlib.sha256(body).hexdigest()
    assert headers["IOT-Open-Sign"] == "8d4c8f2771f9f7f419fd4cbec1d0f1e6"


def test_empty_post_body_signing() -> None:
    """Empty POST body must use SHA256 of empty bytes."""
    secret = decrypt_open_secret(SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED)
    headers = build_open_headers(
        method="POST",
        query="x=",
        body=b"",
        app_id=SISELI_APP_ID,
        app_secret=secret,
        timezone="UTC",
        nonce="nonce-123",
    )
    assert (
        headers["IOT-Open-Body-Hash"]
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    assert headers["IOT-Open-Sign"] == "9f8506bc2a8f3da76eebc4f99691d271"


async def test_header_generation_includes_required_iot_open_values() -> None:
    """Request hook injects required IOT-Open-* and timezone headers."""
    secret = decrypt_open_secret(SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED)

    client = _MockSiseliClient()
    attach_open_auth(client)
    assert len(client._http.event_hooks["request"]) == 1

    request = httpx.Request(
        "POST",
        "https://solar.siseli.com/apis/login/account",
        content=b'{"account":"u","password":"p"}',
    )
    await client._http.event_hooks["request"][0](request)

    for key in (
        "IOT-Time-Zone",
        "IOT-Open-AppID",
        "IOT-Open-Nonce",
        "IOT-Open-Body-Hash",
        "IOT-Open-Sign",
    ):
        assert key in request.headers
    assert request.headers["IOT-Time-Zone"] == "Europe/Moscow"
    assert request.headers["IOT-Open-AppID"] == SISELI_APP_ID
    expected_hash = _sha256_hex(request.content)
    assert request.headers["IOT-Open-Body-Hash"] == expected_hash
    assert request.headers["IOT-Open-Sign"]
    assert request.headers["IOT-Open-Sign"] != secret
