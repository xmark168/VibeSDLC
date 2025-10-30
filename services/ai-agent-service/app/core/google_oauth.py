from authlib.integrations.httpx_client import AsyncOAuth2Client
from app.core.config import settings
import httpx

class GoogleOAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.client_url = settings.GOOGLE_CLIENT_URL

    async def get_authorization_url(self, state: str) -> str:
        """Tạo URL để redirect user đến Google OAuth"""
        client = AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri
        )