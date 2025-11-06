import time
import jwt
import requests
import logging
from github import Github
from typing import Optional
from sqlmodel import Session

logger = logging.getLogger(__name__)


class GitHubAppClient:
    """
    A helper class for GitHub App authentication using installation tokens.
    Automatically renews the token when expired.

    Can be initialized with either:
    1. Direct installation_id and private_key or private_key_path
    2. Database session and installation_id (will fetch from DB)
    """

    def __init__(
        self,
        app_id: str,
        installation_id: int,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
        session: Optional[Session] = None,
    ):
        self.app_id = app_id
        self.installation_id = installation_id
        self.private_key = private_key
        self.private_key_path = private_key_path
        self.session = session

        self._cached_token = None
        self._expiry = 0

        # Validate that at least one key source is provided
        if not self.private_key and not self.private_key_path:
            raise ValueError("Either private_key or private_key_path must be provided")

    def validate_installation_exists(self) -> bool:
        """
        Validate that the installation exists in the database.
        Returns True if installation exists, False otherwise.
        """
        if not self.session:
            logger.warning("No database session provided, skipping installation validation")
            return True

        try:
            from app import crud
            installation = crud.github_installation.get_github_installation_by_installation_id(
                self.session, self.installation_id
            )
            if not installation:
                logger.error(f"GitHub installation {self.installation_id} not found in database")
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating installation: {e}")
            return False

    def _generate_jwt(self) -> str:
        """Generate a JWT signed with the app's private key (valid for 10 minutes)."""
        # Get private key from either direct content or file path
        if self.private_key:
            private_key_content = self.private_key
        elif self.private_key_path:
            with open(self.private_key_path, "r") as f:
                private_key_content = f.read()
        else:
            raise ValueError("No private key available")

        now = int(time.time())
        payload = {
            "iat": now - 60,  # issued 1 min ago to handle clock skew
            "exp": now + (10 * 60),  # expires in 10 min
            "iss": self.app_id
        }

        return jwt.encode(payload, private_key_content, algorithm="RS256")

    def _fetch_installation_token(self) -> dict:
        """Fetch a new installation access token from GitHub."""
        jwt_token = self._generate_jwt()

        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json"
        }

        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        response = requests.post(url, headers=headers)

        if response.status_code == 404:
            logger.error(f"GitHub installation {self.installation_id} not found or revoked")
            # Delete from database if installation was revoked
            if self.session:
                try:
                    from app import crud
                    crud.github_installation.delete_github_installation_by_installation_id(
                        self.session, self.installation_id
                    )
                    logger.info(f"Deleted revoked installation {self.installation_id} from database")
                except Exception as e:
                    logger.error(f"Error deleting revoked installation: {e}")
            raise Exception(f"GitHub installation revoked or not found: {response.status_code}")

        if response.status_code != 201:
            logger.error(f"Failed to get access token: {response.status_code} {response.text}")
            raise Exception(f"Failed to get access token: {response.status_code} {response.text}")

        data = response.json()
        return {
            "token": data["token"],
            "expires_at": data["expires_at"]
        }

    def _get_valid_token(self) -> str:
        """Return a valid token, refresh if expired."""
        now = time.time()
        if not self._cached_token or now > self._expiry - 60:
            token_data = self._fetch_installation_token()
            self._cached_token = token_data["token"]
            self._expiry = time.mktime(time.strptime(token_data["expires_at"], "%Y-%m-%dT%H:%M:%SZ"))

        return self._cached_token

    def get_github(self) -> Github:
        """Return a PyGithub instance with a valid token."""
        token = self._get_valid_token()
        return Github(token)
