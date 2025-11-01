from fastapi import APIRouter, Depends, HTTPException
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser
from app.schemas import Message

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=501,
)
def test_email(email_to: EmailStr) -> Message:
    """
    Test emails - DISABLED (requires email configuration)
    """
    raise HTTPException(
        status_code=501,
        detail="Email service is not configured"
    )


@router.get("/health-check/")
async def health_check() -> bool:
    return True
