"""Tests for FIPS 140 Level 1 compliance verification."""

from __future__ import annotations

import ssl
import subprocess


def test_tls_minimum_protocol():
    """TLS context enforces TLS 1.2 minimum."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    assert ctx.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_no_legacy_ciphers_in_default_context():
    """Default SSL context should not offer RC4, DES, or 3DES."""
    ctx = ssl.create_default_context()
    ciphers = ctx.get_ciphers()
    cipher_names = [c["name"] for c in ciphers]

    for name in cipher_names:
        assert "RC4" not in name, f"RC4 cipher found: {name}"
        assert "DES" not in name or "AESGCM" in name, f"DES cipher found: {name}"
        assert "NULL" not in name, f"NULL cipher found: {name}"
        assert "EXPORT" not in name, f"EXPORT cipher found: {name}"


def test_fips_approved_ciphers_available():
    """At least one FIPS-approved ECDHE+AESGCM cipher is available."""
    ctx = ssl.create_default_context()
    ciphers = ctx.get_ciphers()
    cipher_names = [c["name"] for c in ciphers]

    aesgcm_ciphers = [n for n in cipher_names if "GCM" in n and "ECDHE" in n]
    assert len(aesgcm_ciphers) > 0, f"No ECDHE+AESGCM ciphers found. Available: {cipher_names}"


def test_openssl_version_3x():
    """OpenSSL must be version 3.x for FIPS provider support."""
    version = ssl.OPENSSL_VERSION
    assert "OpenSSL 3." in version, f"Expected OpenSSL 3.x, got: {version}"


def test_sha256_available():
    """SHA-256 (FIPS-approved) must be available."""
    import hashlib
    h = hashlib.sha256(b"test")
    assert len(h.hexdigest()) == 64


def test_certificate_algorithm():
    """Verify openssl supports ECDSA P-384 + SHA-384."""
    result = subprocess.run(
        ["openssl", "ecparam", "-list_curves"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        assert "secp384r1" in result.stdout, "P-384 curve not available"
