"""
Tests — Authentication
=======================
Unit and integration tests for auth endpoints.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAuthService:
    def test_password_hash_and_verify(self):
        from app.services.auth_service import AuthService
        pwd = "SecurePass123!"
        hashed = AuthService.get_password_hash(pwd)
        assert AuthService.verify_password(pwd, hashed)
        assert not AuthService.verify_password("wrong", hashed)

    def test_create_access_token(self):
        from app.services.auth_service import AuthService
        token = AuthService.create_access_token(data={"sub": "test-user-id"})
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_sub(self):
        from app.services.auth_service import AuthService
        from jose import jwt
        from app.config import settings
        token = AuthService.create_access_token(data={"sub": "user-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "user-123"

    def test_expired_token_raises(self):
        from app.services.auth_service import AuthService
        from jose import jwt, JWTError
        from app.config import settings
        from datetime import timedelta
        token = AuthService.create_access_token(
            data={"sub": "user-123"},
            expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(JWTError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

    def test_invalid_token_raises(self):
        from jose import jwt, JWTError
        from app.config import settings
        with pytest.raises(JWTError):
            jwt.decode("invalid.token.here", settings.SECRET_KEY, algorithms=["HS256"])
