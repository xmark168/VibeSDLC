"""Authentication and token schemas."""

from sqlmodel import SQLModel


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    user_id: str | None = None


class TokenPayload(SQLModel):
    sub: str | None = None  # subject - user ID in JWT standard
    type: str | None = None  # token type (access/refresh)


class RefreshTokenRequest(SQLModel):
    refresh_token: str


class LoginRequest(SQLModel):
    email: str
    password: str | None = None
    fullname: str | None = None
    login_provider: str | None = None


class LoginResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(SQLModel):
    email: str
    password: str
    confirm_password: str
    full_name: str | None = None


class RegisterResponse(SQLModel):
    message: str
    email: str


class ConfirmCodeRequest(SQLModel):
    email: str
    code: str


class ConfirmCodeResponse(SQLModel):
    message: str


class ResendCodeRequest(SQLModel):
    email: str


class ResendCodeResponse(SQLModel):
    message: str
    email: str


class RefreshTokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(SQLModel):
    message: str


class ForgotPasswordRequest(SQLModel):
    email: str


class ForgotPasswordResponse(SQLModel):
    message: str
    email: str
    expires_in: int


class ResetPasswordRequest(SQLModel):
    token: str
    new_password: str
    confirm_password: str


class ResetPasswordResponse(SQLModel):
    message: str
