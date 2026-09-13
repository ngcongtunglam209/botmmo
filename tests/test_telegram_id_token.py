"""verify_id_token phải chấp nhận mọi alg Telegram công bố trong JWKS."""

import json
import time
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from app.web import security
from app.web.security import b64url_encode

CLIENT_ID = "8977440531"


def _b64int(value: int, size: int) -> str:
    return b64url_encode(value.to_bytes(size, "big"))


def _make(alg: str):
    """Trả (jwk, sign(data)->bytes)."""
    if alg == "RS256":
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        nums = priv.public_key().public_numbers()
        jwk = {"kty": "RSA", "e": _b64int(nums.e, 3), "n": _b64int(nums.n, 256)}
        return jwk, lambda data: priv.sign(data, padding.PKCS1v15(), hashes.SHA256())
    if alg in ("ES256", "ES256K"):
        curve, crv = (ec.SECP256R1(), "P-256") if alg == "ES256" else (ec.SECP256K1(), "secp256k1")
        priv = ec.generate_private_key(curve)
        nums = priv.public_key().public_numbers()
        jwk = {"kty": "EC", "crv": crv, "x": _b64int(nums.x, 32), "y": _b64int(nums.y, 32)}

        def sign(data):
            r, s = decode_dss_signature(priv.sign(data, ec.ECDSA(hashes.SHA256())))
            return r.to_bytes(32, "big") + s.to_bytes(32, "big")

        return jwk, sign
    priv = ed25519.Ed25519PrivateKey.generate()
    from cryptography.hazmat.primitives import serialization

    raw = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"kty": "OKP", "crv": "Ed25519", "x": b64url_encode(raw)}, priv.sign


def _token(alg: str, sign, claims: dict) -> str:
    header = b64url_encode(json.dumps({"alg": alg, "kid": f"k-{alg}"}).encode())
    payload = b64url_encode(json.dumps(claims).encode())
    return f"{header}.{payload}.{b64url_encode(sign(f'{header}.{payload}'.encode()))}"


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(telegram_client_id=CLIENT_ID))


@pytest.mark.parametrize("alg", ["RS256", "ES256", "ES256K", "EdDSA"])
def test_verify_id_token_all_algs(alg):
    jwk, sign = _make(alg)
    jwks = {"keys": [{**jwk, "kid": f"k-{alg}"}]}
    now = int(time.time())
    claims = {"iss": security.TELEGRAM_ISSUER, "aud": int(CLIENT_ID), "sub": "1",
              "iat": now, "exp": now + 300, "nonce": "n1"}
    token = _token(alg, sign, claims)

    assert security.verify_id_token(token, jwks, "n1")["sub"] == "1"
    assert security.verify_id_token(token, jwks, "other") == {}

    header, payload, sig = token.split(".")
    tampered = b64url_encode(json.dumps({**claims, "sub": "2"}).encode())
    assert security.verify_id_token(f"{header}.{tampered}.{sig}", jwks, "n1") == {}
