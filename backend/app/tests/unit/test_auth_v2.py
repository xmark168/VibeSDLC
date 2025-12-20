"""Unit tests for Authentication Module with mocks"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, call
from fastapi import HTTPException
from uuid import uuid4, UUID
import time
import asyncio
from typing import Dict, Optional
import secrets
import hashlib


def _slow_validator(value, delay=0.01):
    time.sleep(delay)
    return True

def _email_validator(email):
    import re
    time.sleep(0.005)
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))

def _password_validator(password):
    time.sleep(0.005)
    if len(password) < 8: return False
    has_letter = bool(__import__('re').search(r"[a-zA-Z]", password))
    has_number = bool(__import__('re').search(r"\d", password))
    return has_letter and has_number


class TestLoginCredential:
    def test_login_success_with_valid_credentials(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.login_provider = None
        mock_user.hashed_password = "hashed_valid_pass"

        with patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
             patch('app.core.security.verify_password', return_value=True), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            from app.api.auth import login  # assuming login function exists
            result = login("valid@example.com", "ValidPass123")
            assert result is not None

    def test_login_with_wrong_password_raises_401(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.login_provider = None
        mock_user.hashed_password = "different_hash"

        with patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
             patch('app.core.security.verify_password', return_value=False), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import login
                login("user@example.com", "WrongPass123")
            assert exc_info.value.status_code == 401

    def test_login_with_nonexistent_user_raises_404(self):
        with patch('app.services.user_service.get_user_by_email', return_value=None), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import login
                login("nonexistent@example.com", "any_password")
            assert exc_info.value.status_code == 404

    def test_login_with_inactive_account_raises_403(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = False  # Inactive
        mock_user.is_locked = False
        mock_user.login_provider = None
        mock_user.hashed_password = "hashed_pass"

        with patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
             patch('app.core.security.verify_password', return_value=True), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import login
                login("inactive@example.com", "ValidPass123")
            assert exc_info.value.status_code == 403

    def test_login_with_locked_account_raises_423(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = True
        mock_user.is_locked = True  # Locked
        mock_user.login_provider = None
        mock_user.hashed_password = "hashed_pass"

        with patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
             patch('app.core.security.verify_password', return_value=True), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import login
                login("locked@example.com", "ValidPass123")
            assert exc_info.value.status_code == 423

    def test_login_oauth_user_with_credential_raises_400(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.login_provider = "google"  # OAuth provider
        mock_user.hashed_password = None  # No password for OAuth

        with patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import login
                login("oauth@example.com", "any_password")
            assert exc_info.value.status_code == 400


class TestRegister:
    def test_register_success_with_valid_data(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "new@example.com"
        mock_user.full_name = "New User"

        with patch('app.services.user_service.get_user_by_email', return_value=None), \
             patch('app.services.user_service.create_user', return_value=mock_user), \
             patch('app.services.email_service.send_welcome_email', return_value=AsyncMock()), \
             patch('app.core.security.hash_password', return_value="hashed"), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            from app.api.auth import register
            result = register("new@example.com", "ValidPass123", "New User", "ValidPass123")
            assert result["email"] == "new@example.com"

    def test_register_with_email_already_exists_raises_409(self):
        existing_user = MagicMock()
        existing_user.login_provider = None  # Credential user

        with patch('app.services.user_service.get_user_by_email', return_value=existing_user), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("existing@example.com", "ValidPass123", "User", "ValidPass123")
            assert exc_info.value.status_code == 409

    def test_register_with_oauth_email_raises_409(self):
        existing_user = MagicMock()
        existing_user.login_provider = "google"  # OAuth provider

        with patch('app.services.user_service.get_user_by_email', return_value=existing_user), \
             patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("oauth@example.com", "ValidPass123", "User", "ValidPass123")
            assert exc_info.value.status_code == 409

    def test_register_with_invalid_email_format_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.005)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("invalid-email", "ValidPass123", "User", "ValidPass123")
            assert exc_info.value.status_code == 400

    def test_register_with_short_password_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.005)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("user@example.com", "Short1", "User", "Short1")
            assert exc_info.value.status_code == 400

    def test_register_with_password_no_letter_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.005)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("user@example.com", "12345678", "User", "12345678")
            assert exc_info.value.status_code == 400

    def test_register_with_password_no_number_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.005)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("user@example.com", "NoNumbersHere", "User", "NoNumbersHere")
            assert exc_info.value.status_code == 400

    def test_register_with_password_mismatch_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("user@example.com", "ValidPass123", "User", "DifferentPass456")
            assert exc_info.value.status_code == 400

    def test_register_with_long_fullname_raises_400(self):
        long_name = "A" * 51
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("user@example.com", "ValidPass123", long_name, "ValidPass123")
            assert exc_info.value.status_code == 400

    def test_register_with_empty_fullname_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import register
                register("user@example.com", "ValidPass123", "", "ValidPass123")
            assert exc_info.value.status_code == 400


class TestConfirmCode:
    def test_confirm_success_with_valid_code(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.services.user_service.get_user_by_email') as mock_get_user, \
             patch('app.services.user_service.update_user') as mock_update_user:
            mock_user = MagicMock()
            mock_user.id = uuid4()
            mock_user.is_active = False  # Not confirmed
            mock_get_user.return_value = mock_user
            mock_update_user.return_value = MagicMock(is_active=True)
            
            from app.api.auth import confirm_code
            result = confirm_code("123456", "valid@example.com")
            assert result is not None

    def test_confirm_with_expired_code_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import confirm_code
                confirm_code("expired", "expired@example.com")
            assert exc_info.value.status_code == 400

    def test_confirm_with_wrong_code_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import confirm_code
                confirm_code("wrong_code", "user@example.com")
            assert exc_info.value.status_code == 400

    def test_confirm_with_nonexistent_registration_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import confirm_code
                confirm_code("123456", "nonexistent@example.com")
            assert exc_info.value.status_code == 400


class TestRefreshToken:
    def test_refresh_success_with_valid_token(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = True
        mock_user.is_locked = False

        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.decode_token', return_value={"sub": str(uuid4()), "type": "refresh"}), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user):
            from app.api.auth import refresh_token
            result = refresh_token("valid_refresh_token")
            assert "access_token" in result

    def test_refresh_with_inactive_user_raises_403(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = False  # Inactive
        mock_user.is_locked = False

        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.decode_token', return_value={"sub": str(uuid4()), "type": "refresh"}), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import refresh_token
                refresh_token("valid_token")
            assert exc_info.value.status_code == 403

    def test_refresh_with_locked_user_raises_423(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.is_active = True
        mock_user.is_locked = True  # Locked

        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.decode_token', return_value={"sub": str(uuid4()), "type": "refresh"}), \
             patch('app.services.user_service.get_user_by_id', return_value=mock_user):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import refresh_token
                refresh_token("valid_token")
            assert exc_info.value.status_code == 423

    def test_refresh_with_invalid_token_raises_401(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.decode_token', side_effect=Exception("Invalid token")):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import refresh_token
                refresh_token("invalid_token")
            assert exc_info.value.status_code == 401

    def test_refresh_with_nonexistent_user_raises_404(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.decode_token', return_value={"sub": str(uuid4()), "type": "refresh"}), \
             patch('app.services.user_service.get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import refresh_token
                refresh_token("valid_token")
            assert exc_info.value.status_code == 404

    def test_refresh_with_no_token_raises_401(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import refresh_token
                refresh_token(None)
            assert exc_info.value.status_code == 401


class TestForgotPassword:
    def test_forgot_password_success_with_existing_user(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "forgot@example.com"

        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
             patch('app.services.email_service.send_password_reset_email', return_value=AsyncMock()):
            from app.api.auth import forgot_password
            result = forgot_password("forgot@example.com")
            assert result["message"] == "Email sent if account exists"

    def test_forgot_password_with_nonexistent_user_returns_success(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.services.user_service.get_user_by_email', return_value=None):
            from app.api.auth import forgot_password
            result = forgot_password("nonexistent@example.com")
            assert result["message"] == "Email sent if account exists"

    def test_forgot_password_with_invalid_email_format_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.005)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import forgot_password
                forgot_password("invalid-email-format")
            assert exc_info.value.status_code == 400


class TestResetPassword:
    def test_reset_success_with_valid_token(self):
        mock_user = MagicMock()
        mock_user.id = uuid4()

        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.get_email_from_reset_token', return_value="reset@example.com"), \
             patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
             patch('app.services.user_service.update_user_password', return_value=mock_user), \
             patch('app.core.security.hash_password', return_value="new_hashed_password"):
            from app.api.auth import reset_password
            result = reset_password("valid_token", "NewValidPass123", "NewValidPass123")
            assert "Password reset successfully" in result["message"]

    def test_reset_with_invalid_token_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.get_email_from_reset_token', side_effect=Exception("Invalid token")):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import reset_password
                reset_password("invalid_token", "NewPass123", "NewPass123")
            assert exc_info.value.status_code == 400

    def test_reset_with_password_mismatch_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import reset_password
                reset_password("valid_token", "NewPass123", "DifferentPass456")
            assert exc_info.value.status_code == 400

    def test_reset_with_invalid_password_format_raises_400(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.005)):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import reset_password
                reset_password("valid_token", "short", "short")
            assert exc_info.value.status_code == 400

    def test_reset_with_nonexistent_user_raises_404(self):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.02)), \
             patch('app.core.security.get_email_from_reset_token', return_value="user@example.com"), \
             patch('app.services.user_service.get_user_by_email', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                from app.api.auth import reset_password
                reset_password("valid_token", "NewValidPass123", "NewValidPass123")
            assert exc_info.value.status_code == 404


class TestEmailValidation:
    @pytest.mark.parametrize("email", [
        "user@example.com", "test.email@domain.co.uk", "user+tag@example.org", 
        "user123@test-domain.com", "a@b.co", "user_name@example-name.com"
    ])
    def test_valid_email_formats(self, email):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            assert _email_validator(email) is True
    
    @pytest.mark.parametrize("email", [
        "invalid-email", "@invalid.com", "invalid@", "invalid@.com", "", 
        "user@domain", "user name@example.com", "user@", "@example.com", "user..user@example.com"
    ])
    def test_invalid_email_formats(self, email):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.002)):
            assert _email_validator(email) is False


class TestPasswordValidation:
    @pytest.mark.parametrize("password", [
        "ValidPass123", "LongPasswordWith123!@#", "TestPass456", 
        "SecurePass999", "MyPassword1"
    ])
    def test_valid_password_formats(self, password):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0015)):
            assert _password_validator(password) is True
    
    @pytest.mark.parametrize("password", [
        "short", "12345678", "NoNumbers", "abc", "", "a" * 7
    ])
    def test_invalid_password_formats(self, password):
        with patch('time.sleep', side_effect=lambda x: time.sleep(0.0015)):
            assert _password_validator(password) is False


def test_multiple_concurrent_operations():
    import concurrent.futures
    
    def op_runner(n):
        time.sleep(0.01)
        return f"result_{n}"
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(op_runner, i) for i in range(3)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    assert len(results) == 3


def test_comprehensive_auth_flow():
    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.email = "comprehensive@example.com"
    mock_user.is_active = True
    mock_user.is_locked = False
    mock_user.hashed_password = "hashed"

    with patch('app.services.user_service.get_user_by_email', return_value=mock_user), \
         patch('app.core.security.verify_password', return_value=True), \
         patch('app.core.security.decode_token', return_value={"sub": str(uuid4()), "type": "refresh"}), \
         patch('app.services.user_service.get_user_by_id', return_value=mock_user), \
         patch('app.core.security.get_email_from_reset_token', return_value="comprehensive@example.com"), \
         patch('app.services.user_service.update_user_password', return_value=mock_user), \
         patch('app.core.security.hash_password', return_value="new_hashed"), \
         patch('time.sleep', side_effect=lambda x: time.sleep(0.015)):
        
        from app.api.auth import login
        login_result = login("comprehensive@example.com", "ValidPass123")
        assert login_result is not None
        
        from app.api.auth import refresh_token
        refresh_result = refresh_token("valid_refresh_token")
        assert "access_token" in refresh_result
        
        from app.api.auth import forgot_password
        forgot_result = forgot_password("comprehensive@example.com")
        assert forgot_result["message"] == "Email sent if account exists"
        
        from app.api.auth import reset_password
        reset_result = reset_password("valid_token", "NewValidPass456", "NewValidPass456")
        assert "Password reset successfully" in reset_result["message"]