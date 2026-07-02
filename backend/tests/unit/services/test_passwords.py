"""Pruebas de hash y verificación de contraseñas."""

from __future__ import annotations

from app.services.passwords import hash_password, verify_password


class TestPasswords:
    def test_hash_and_verify_success(self):
        hashed = hash_password("MiClaveSegura123")
        assert verify_password("MiClaveSegura123", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correcta")
        assert verify_password("incorrecta", hashed) is False

    def test_invalid_hash_returns_false(self):
        assert verify_password("cualquiera", "not-a-bcrypt-hash") is False

    def test_different_hashes_for_same_password(self):
        a = hash_password("same-password")
        b = hash_password("same-password")
        assert a != b
        assert verify_password("same-password", a)
        assert verify_password("same-password", b)
