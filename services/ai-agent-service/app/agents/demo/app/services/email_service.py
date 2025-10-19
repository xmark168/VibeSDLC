from typing import Optional
from fastapi import HTTPException, status
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr

class EmailService:
    def __init__(self, email_config: ConnectionConfig):
        self.email_config = email_config
        self.fast_mail = FastMail(self.email_config)

    async def send_verification_email(self, email: EmailStr, token: str) -> None:
        try:
            message = MessageSchema(
                subject="Email Verification",
                recipients=[email],
                subtype="html"
            )
            await self.fast_mail.send_message(message)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email."
            ) from e

    async def send_password_reset_email(self, email: EmailStr, token: str) -> None:
        try:
            message = MessageSchema(
                subject="Password Reset",
                recipients=[email],
                subtype="html"
            )
            await self.fast_mail.send_message(message)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email."
            ) from e