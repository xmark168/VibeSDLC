from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm

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


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.authenticate(
        session=session, email_or_username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email/username or password")

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token = crud.create_refresh_token(session=session, user_id=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token.token,
        token_type="bearer"
    )


@router.post("/login")
def login(session: SessionDep, user_login: UserLogin) -> Token:
    """
    Login with email or username and password
    """
    user = crud.authenticate(
        session=session,
        email_or_username=user_login.email_or_username,
        password=user_login.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email/username or password")

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token = crud.create_refresh_token(session=session, user_id=user.id)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token.token,
        token_type="bearer"
    )


@router.post("/login/refresh")
def refresh_access_token(session: SessionDep, body: RefreshTokenRequest) -> Token:
    """
    Refresh access token using refresh token
    """
    # Validate refresh token
    db_token = crud.validate_refresh_token(session=session, token=body.refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Get user
    user = session.get(User, db_token.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    # Optionally create new refresh token (rotate refresh tokens)
    new_refresh_token = crud.create_refresh_token(session=session, user_id=user.id)

    # Revoke old refresh token
    crud.revoke_refresh_token(session=session, token=body.refresh_token)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token.token,
        token_type="bearer"
    )


@router.post("/logout")
def logout(session: SessionDep, body: RefreshTokenRequest) -> Message:
    """
    Logout - revoke refresh token
    """
    success = crud.revoke_refresh_token(session=session, token=body.refresh_token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    return Message(message="Successfully logged out")


@router.post("/register", response_model=UserPublic)
def register(session: SessionDep, user_register: UserRegister) -> Any:
    """
    Register new user
    """
    # Check if user already exists
    existing_user = crud.get_user_by_email(session=session, email=user_register.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_user = crud.get_user_by_username(session=session, username=user_register.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken")

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
