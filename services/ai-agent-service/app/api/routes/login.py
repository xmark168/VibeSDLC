from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import User
from app.schemas import (
    Token,
    UserPublic,
    UserLogin,
    RefreshTokenRequest,
    Message,
    NewPassword,
    UserRegister
)
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/login/access-token")
@limiter.limit("5/minute")  # Rate limit: 5 requests per minute per IP
def login_access_token(
    request: Request,
    response: Response,
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login with security best practices:
    - Rate limiting (5 req/min)
    - HttpOnly cookie for refresh token
    - Account locking after failed attempts
    - Token rotation detection
    """
    user = crud.authenticate(
        session=session, email_or_username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Create access token with scopes
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        token_type="access"
    )

    # Create refresh token
    refresh_token = crud.create_refresh_token(session=session, user_id=user.id)

    # Set refresh token in HttpOnly cookie for security
    response.set_cookie(
        key="refresh_token",
        value=refresh_token.token,
        httponly=True,      # Prevents JavaScript access (XSS protection)
        secure=True,        # Only send over HTTPS
        samesite="lax",     # CSRF protection
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=f"{settings.API_V1_STR}/login"  # Only send to login endpoints
    )

    # Only return access token in JSON (NOT refresh token)
    return Token(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/login/refresh")
@limiter.limit("10/minute")  # Allow more frequent token refreshes
def refresh_access_token(
    request: Request,
    response: Response,
    session: SessionDep
) -> Token:
    """
    Refresh access token using HttpOnly cookie
    Implements token rotation for security
    """
    # Get refresh token from HttpOnly cookie
    refresh_token_str = request.cookies.get("refresh_token")
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Validate refresh token (includes rotation detection)
    db_token = crud.validate_refresh_token(session=session, token=refresh_token_str)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Get user
    user = session.get(User, db_token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=access_token_expires,
        token_type="access"
    )

    # Token rotation: Create new refresh token
    new_refresh_token = crud.create_refresh_token(
        session=session,
        user_id=user.id,
        family_id=db_token.family_id,  # Keep same family
        parent_token_id=db_token.id     # Track parent
    )

    # Revoke old refresh token
    crud.revoke_refresh_token(session=session, token=refresh_token_str)

    # Set new refresh token in HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token.token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=f"{settings.API_V1_STR}/login"
    )

    return Token(
        access_token=access_token,
        token_type="bearer"
    )


@router.post("/logout")
def logout(request: Request, response: Response, session: SessionDep) -> Message:
    """
    Logout - revoke refresh token from HttpOnly cookie
    """
    refresh_token_str = request.cookies.get("refresh_token")
    if refresh_token_str:
        crud.revoke_refresh_token(session=session, token=refresh_token_str)

    # Clear the cookie
    response.delete_cookie(
        key="refresh_token",
        path=f"{settings.API_V1_STR}/login"
    )

    return Message(message="Successfully logged out")


@router.post("/register", response_model=UserPublic)
@limiter.limit("3/hour")  # Prevent spam registrations
def register(request: Request, session: SessionDep, user_register: UserRegister) -> Any:
    """
    Register new user with rate limiting
    """
    # Check if user already exists
    existing_user = crud.get_user_by_email(session=session, email=user_register.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    existing_user = crud.get_user_by_username(session=session, username=user_register.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    from app.schemas import UserCreate
    user_create = UserCreate(
        username=user_register.username,
        email=user_register.email,
        password=user_register.password
    )
    user = crud.create_user(session=session, user_create=user_create)
    return user


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Password recovery email sent")


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this email does not exist in the system.",
        )
    hashed_password = get_password_hash(password=body.new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )
