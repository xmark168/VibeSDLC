import random
import re
import secrets
import logging
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Cookie
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.services import UserService
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.security import get_password_hash, verify_password
from app.models import User
from app.schemas import (
    Token,
    UserPublic,
    UserLogin,
    RefreshTokenRequest,
    Message,
    NewPassword,
    UserRegister,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ConfirmCodeRequest,
    ConfirmCodeResponse,
    ResendCodeRequest,
    ResendCodeResponse,
    RefreshTokenResponse,
    LogoutResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.utils import (
    generate_password_reset_email,
    generate_password_reset_token,
    generate_reset_password_email,
    generate_verification_code_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["authentication"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Redis client
redis_client = get_redis_client()



def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> bool:
    """Validate password: min 8 chars, at least 1 letter and 1 number"""
    if len(password) < 8:
        return False
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_number = bool(re.search(r'\d', password))
    return has_letter and has_number


def generate_verification_code() -> str:
    """Generate 6-digit verification code"""
    return str(random.randint(100000, 999999))


@router.post("/login/access-token", response_model=LoginResponse)
@limiter.limit("5/minute")
def login_access_token(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep
) -> LoginResponse:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Convert OAuth2 form to LoginRequest format
    login_data = LoginRequest(
        email=form_data.username,  # OAuth2 uses 'username' field for email
        password=form_data.password,
        login_provider=False
    )

    # Reuse the main login logic
    return login(request=request, response=response, login_data=login_data, session=session)


@router.post("/login", response_model=LoginResponse)
# @limiter.limit("5/minute")  # Temporarily disabled for debugging
def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    session: SessionDep
) -> LoginResponse:
    """
    Login API - supports both credential and OAuth provider login
    """
    if not login_data.loginProvider:
        # Credential Login
        if not login_data.email or not login_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email và password không được để trống với credential login"
            )

        # Admin bypass - if email is "admin" and password is "admin", allow login
        if str(login_data.email).lower() == "admin@gmail.com" and login_data.password == "admin":
            # Find or create admin user
            user_service = UserService(session)
            user = user_service.get_by_email("admin@gmail.com")
            if not user:
                # Create admin user if doesn't exist
                from app.models import User, Role
                user = User(
                    email="admin@gmail.com",
                    full_name="Administrator",
                    hashed_password=get_password_hash("admin"),
                    is_active=True,
                    is_locked=False,
                    login_provider=False,
                    role=Role.ADMIN
                )
                session.add(user)
                session.commit()
                session.refresh(user)
        else:
            # Find user with credential login
            user_service = UserService(session)
            user = user_service.get_by_email(str(login_data.email))
            if not user or user.login_provider:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email hoặc mật khẩu không đúng"
                )

            # Verify password
            if not verify_password(login_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email hoặc mật khẩu không đúng"
                )

    else:
        # Provider Login
        # if not login_data.email or not login_data.full_name or login_data.password is not None:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Email và fullname không được để trống, password phải null với provider login"
        #     )

        # Find or create user with provider login
        user_service = UserService(session)
        user = user_service.get_by_email(str(login_data.email))
        if not user:
            # Create new user for provider login
            from app.models import User
            user = User(
                email=login_data.email,
                full_name=login_data.full_name,
                login_provider=True,
                is_active=True,
                is_locked=False
            )
            session.add(user)
            session.commit()
            session.refresh(user)

    # Check account status
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa"
        )

    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Tài khoản đã bị khóa"
        )

    # Create tokens
    access_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access"
    )

    refresh_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh"
    )

    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return LoginResponse(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/register", response_model=RegisterResponse)
@limiter.limit("3/minute")
def register(
    request: Request,
    register_data: RegisterRequest,
    session: SessionDep
) -> RegisterResponse:
    """
    Register API - create new account with credential
    """
    # Debug: Log received data
    logger.info(f"Register request received: email={register_data.email}, fullname={register_data.fullname}, has_password={bool(register_data.password)}, has_confirmPassword={bool(register_data.confirmPassword)}")

    # Validation
    if not validate_email(str(register_data.email)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Định dạng email không hợp lệ"
        )

    if register_data.fullname and (len(register_data.fullname) > 50 or not register_data.fullname.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Họ tên không được rỗng và tối đa 50 ký tự"
        )

    if not validate_password(register_data.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mật khẩu phải có ít nhất 8 ký tự, chứa ít nhất 1 chữ cái và 1 chữ số"
        )

    if register_data.password != register_data.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mật khẩu xác nhận không khớp"
        )

    # Check if email already exists with credential login
    user_service = UserService(session)
    existing_user = user_service.get_by_email(str(register_data.email))
    if existing_user and not existing_user.login_provider:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email này đã được đăng ký"
        )

    # Generate verification code
    code = generate_verification_code()

    # Store registration data in Redis (separate keys with different TTLs)
    registration_data = {
        "email": str(register_data.email),
        "full_name": register_data.full_name,
        "hashed_password": get_password_hash(register_data.password)
    }

    registration_key = f"registration:{register_data.email}"
    verification_key = f"verification_code:{register_data.email}"

    # Store registration data with 30 minutes TTL
    if not redis_client.set(registration_key, registration_data, ttl=1800):  # 30 minutes
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống, vui lòng thử lại"
        )

    # Store verification code with 3 minutes TTL
    if not redis_client.set(verification_key, code, ttl=180):  # 3 minutes
        # Clean up registration data if verification code storage fails
        redis_client.delete(registration_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống, vui lòng thử lại"
        )

    # Send verification email
    try:
        email_data = generate_verification_code_email(
            email_to=str(register_data.email),
            code=code
        )
        send_email(
            email_to=str(register_data.email),
            subject=email_data.subject,
            html_content=email_data.html_content
        )
    except Exception as e:
        # Clean up Redis data if email fails
        redis_client.delete(registration_key)
        redis_client.delete(verification_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể gửi email xác thực"
        )

    return RegisterResponse(
        message="Mã xác thực đã được gửi đến email của bạn",
        email=register_data.email,
        expires_in=180
    )


@router.post("/confirm-code", response_model=ConfirmCodeResponse)
@limiter.limit("5/minute")
def confirm_code(
    request: Request,
    confirm_data: ConfirmCodeRequest,
    session: SessionDep
) -> ConfirmCodeResponse:
    """
    Confirm verification code and complete registration
    """
    registration_key = f"registration:{confirm_data.email}"
    verification_key = f"verification_code:{confirm_data.email}"

    # Get both registration data and verification code
    registration_data = redis_client.get(registration_key)
    verification_code = redis_client.get(verification_key)

    # Debug logging
    logger.info(f"[OTP DEBUG] Email: {confirm_data.email}")
    logger.info(f"[OTP DEBUG] Received code from client: {confirm_data.code!r} (type: {type(confirm_data.code).__name__})")
    logger.info(f"[OTP DEBUG] Retrieved verification_code from Redis: {verification_code!r} (type: {type(verification_code).__name__})")
    logger.info(f"[OTP DEBUG] Registration data exists: {bool(registration_data)}")

    # Handle edge cases
    if not registration_data and not verification_code:
        logger.warning(f"[OTP DEBUG] Both registration_data and verification_code are missing for {confirm_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dữ liệu đăng ký đã hết hạn. Vui lòng đăng ký lại từ đầu"
        )

    if not registration_data and verification_code:
        logger.warning(f"[OTP DEBUG] Registration data missing but verification_code exists for {confirm_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dữ liệu đăng ký đã hết hạn. Vui lòng đăng ký lại từ đầu"
        )

    if registration_data and not verification_code:
        logger.warning(f"[OTP DEBUG] Verification code missing but registration_data exists for {confirm_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác thực đã hết hạn. Vui lòng yêu cầu gửi lại mã"
        )

    # Verify code - ensure both are strings for comparison
    verification_code_str = str(verification_code).strip() if verification_code else None
    confirm_code_str = str(confirm_data.code).strip() if confirm_data.code else None

    logger.info(f"[OTP DEBUG] After normalization - verification_code: {verification_code_str!r}, confirm_code: {confirm_code_str!r}")
    logger.info(f"[OTP DEBUG] Codes match: {verification_code_str == confirm_code_str}")

    if verification_code_str != confirm_code_str:
        logger.error(f"[OTP DEBUG] Code mismatch for {confirm_data.email}: expected {verification_code_str!r}, got {confirm_code_str!r}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác thực không đúng"
        )

    # Create user
    from app.models import User
    user = User(
        email=registration_data["email"],
        full_name=registration_data["full_name"],
        hashed_password=registration_data["hashed_password"],
        is_active=True,
        is_locked=False,
        login_provider=False
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    # Clean up Redis data (both keys)
    redis_client.delete(registration_key)
    redis_client.delete(verification_key)

    return ConfirmCodeResponse(
        message="Đăng ký thành công",
        user_id=user.id
    )


@router.post("/resend-code", response_model=ResendCodeResponse)
@limiter.limit("2/minute")
def resend_code(
    request: Request,
    resend_data: ResendCodeRequest,
    session: SessionDep
) -> ResendCodeResponse:
    """
    Resend verification code
    """
    registration_key = f"registration:{resend_data.email}"
    verification_key = f"verification_code:{resend_data.email}"

    # Check if registration data still exists
    registration_data = redis_client.get(registration_key)

    if not registration_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dữ liệu đăng ký đã hết hạn. Vui lòng đăng ký lại từ đầu"
        )

    # Generate new verification code
    new_code = generate_verification_code()

    # Store only the new verification code (don't touch registration data)
    if not redis_client.set(verification_key, new_code, ttl=180):  # 3 minutes
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống, vui lòng thử lại"
        )

    # Send new verification email
    try:
        email_data = generate_verification_code_email(
            email_to=str(resend_data.email),
            code=new_code
        )
        send_email(
            email_to=str(resend_data.email),
            subject=email_data.subject,
            html_content=email_data.html_content
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể gửi email xác thực"
        )

    return ResendCodeResponse(
        message="Mã xác thực mới đã được gửi đến email của bạn",
        email=resend_data.email,
        expires_in=180
    )


@router.post("/refresh-token", response_model=RefreshTokenResponse)
@limiter.limit("10/minute")
def refresh_token(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest,
    session: SessionDep,
    refresh_token_cookie: str = Cookie(None, alias="refresh_token")
) -> RefreshTokenResponse:
    """
    Refresh access token using refresh token
    """
    # Get refresh token from request body or cookie
    refresh_token = refresh_data.refresh_token or refresh_token_cookie

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không được cung cấp"
        )

    # Decode and validate refresh token
    try:
        payload = security.decode_access_token(refresh_token)
        logger.info(f"[REFRESH TOKEN] Decoded payload: {payload}")

        if payload.get("type") != "refresh":
            logger.warning(f"[REFRESH TOKEN] Invalid token type: {payload.get('type')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ"
            )

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("[REFRESH TOKEN] Missing user_id in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ"
            )

        logger.info(f"[REFRESH TOKEN] User ID from token: {user_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFRESH TOKEN] Token decode error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ hoặc đã hết hạn"
        )

    # Get user
    logger.info(f"[REFRESH TOKEN] Looking up user with ID: {user_id}")
    user = session.get(User, user_id)
    if not user:
        logger.error(f"[REFRESH TOKEN] User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại"
        )

    logger.info(f"[REFRESH TOKEN] User found: {user.email}, is_active={user.is_active}, is_locked={user.is_locked}")

    # Check user status
    if not user.is_active:
        logger.warning(f"[REFRESH TOKEN] User account disabled: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa"
        )

    if user.is_locked:
        logger.warning(f"[REFRESH TOKEN] User account locked: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Tài khoản đã bị khóa"
        )

    # Create new tokens
    new_access_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access"
    )

    new_refresh_token = security.create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh"
    )

    # Update refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return RefreshTokenResponse(
        user_id=user.id,
        access_token=new_access_token,
        refresh_token=new_refresh_token
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    forgot_data: ForgotPasswordRequest,
    session: SessionDep
) -> ForgotPasswordResponse:
    """
    Forgot Password API - send reset password link via email
    """
    # Validate email format
    if not validate_email(str(forgot_data.email)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Định dạng email không hợp lệ"
        )

    # Check if email exists in database
    user_service = UserService(session)
    user = user_service.get_by_email(str(forgot_data.email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email không tồn tại trong hệ thống"
        )

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)

    # Store token in Redis with email as value
    token_key = f"password_reset:{reset_token}"
    if not redis_client.set(token_key, str(forgot_data.email), ttl=900):  # 15 minutes
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống, vui lòng thử lại"
        )

    # Create reset link
    reset_link = f"{settings.FRONTEND_HOST}/reset-password?token={reset_token}"

    # Send reset password email
    try:
        email_data = generate_password_reset_email(
            email_to=str(forgot_data.email),
            reset_link=reset_link
        )
        send_email(
            email_to=str(forgot_data.email),
            subject=email_data.subject,
            html_content=email_data.html_content
        )
    except Exception as e:
        # Clean up Redis data if email fails
        redis_client.delete(token_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể gửi email reset password"
        )

    return ForgotPasswordResponse(
        message="Link reset mật khẩu đã được gửi đến email của bạn",
        expires_in=900
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
@limiter.limit("5/minute")
def reset_password(
    request: Request,
    reset_data: ResetPasswordRequest,
    session: SessionDep
) -> ResetPasswordResponse:
    """
    Reset Password API - set new password using token
    """
    # Validate new password
    if not validate_password(reset_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mật khẩu phải có ít nhất 8 ký tự, chứa ít nhất 1 chữ cái và 1 chữ số"
        )

    # Check password confirmation
    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu xác nhận không khớp"
        )

    # Get email from Redis using token
    token_key = f"password_reset:{reset_data.token}"
    email = redis_client.get(token_key)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token không hợp lệ hoặc đã hết hạn"
        )

    # Find user by email
    user_service = UserService(session)
    user = user_service.get_by_email(str(email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng không tồn tại"
        )

    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    session.add(user)
    session.commit()

    # Clean up Redis token
    redis_client.delete(token_key)

    return ResetPasswordResponse(
        message="Đặt lại mật khẩu thành công"
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    current_user: CurrentUser,
    session: SessionDep,
) -> LogoutResponse:
    """
    Logout API - clear refresh token cookie and optionally revoke tokens from database

    This endpoint:
    1. Clears the refresh_token cookie from the client
    2. Optionally revokes refresh tokens from database (if using RefreshToken model)

    Args:
        response: FastAPI Response object to manipulate cookies
        current_user: Current authenticated user (from JWT token)
        session: Database session

    Returns:
        LogoutResponse with success message
    """
    try:
        # Clear refresh token cookie by setting max_age to 0
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=True,
            samesite="lax"
        )

        # Optional: Revoke all refresh tokens for this user from database
        # Uncomment if you want to revoke tokens stored in RefreshToken table
        # from app.services import UserService
        # user_service = UserService(session)
        # user_service.revoke_all_user_tokens(current_user.id)



        return LogoutResponse(
            message="Đăng xuất thành công"
        )

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi khi đăng xuất"
        )
