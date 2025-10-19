from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User
from app.schemas import EmailVerificationRequest, EmailVerificationResponse
from app.dependencies import get_db, send_verification_email
from app.utils import create_verification_token, verify_token

router = APIRouter()

@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    verification_request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    # Validate the token
    user_id = verify_token(verification_request.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    # Retrieve user from the database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # Check if the user is already verified
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified."
        )

    # Update user verification status
    user.is_verified = True
    db.add(user)
    await db.commit()

    return EmailVerificationResponse(message="Email verified successfully.")

@router.post("/send-verification-email")
async def send_verification_email_endpoint(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    # Retrieve user from the database
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified."
        )

    # Create verification token
    token = create_verification_token(user.id)

    # Send verification email
    await send_verification_email(email, token)

    return {"message": "Verification email sent."}