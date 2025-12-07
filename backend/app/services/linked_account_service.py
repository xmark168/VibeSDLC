"""Linked Account Service - Manages OAuth account linking."""

from uuid import UUID
from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.models import User, LinkedAccount, OAuthProvider


class LinkedAccountService:
    """Service for managing linked OAuth accounts."""

    ALL_PROVIDERS = [p.value for p in OAuthProvider]

    def __init__(self, session: Session):
        self.session = session

    def get_linked_accounts(self, user_id: UUID) -> list[LinkedAccount]:
        """Get all linked accounts for a user."""
        statement = select(LinkedAccount).where(LinkedAccount.user_id == user_id)
        return list(self.session.exec(statement).all())

    def get_available_providers(self, user_id: UUID) -> list[str]:
        """Get providers that are not yet linked for a user."""
        linked = self.get_linked_accounts(user_id)
        # provider is now stored as string in DB
        linked_providers = {acc.provider for acc in linked}
        return [p for p in self.ALL_PROVIDERS if p not in linked_providers]

    def get_linked_account_by_provider(
        self, user_id: UUID, provider: OAuthProvider
    ) -> LinkedAccount | None:
        """Get a specific linked account by provider."""
        statement = select(LinkedAccount).where(
            LinkedAccount.user_id == user_id,
            LinkedAccount.provider == provider.value  # Use .value for string comparison
        )
        return self.session.exec(statement).first()

    def find_by_provider_user_id(
        self, provider: OAuthProvider, provider_user_id: str
    ) -> LinkedAccount | None:
        """Find a linked account by provider and provider's user ID."""
        statement = select(LinkedAccount).where(
            LinkedAccount.provider == provider.value,  # Use .value for string comparison
            LinkedAccount.provider_user_id == provider_user_id
        )
        return self.session.exec(statement).first()

    def find_user_by_provider(
        self, provider: OAuthProvider, provider_user_id: str
    ) -> User | None:
        """Find the user associated with a provider account."""
        linked = self.find_by_provider_user_id(provider, provider_user_id)
        if linked:
            return self.session.get(User, linked.user_id)
        return None

    def link_account(
        self,
        user_id: UUID,
        provider: OAuthProvider,
        provider_user_id: str,
        provider_email: str,
    ) -> LinkedAccount:
        """Link an OAuth account to a user."""
        # Check if provider already linked to this user
        existing = self.get_linked_account_by_provider(user_id, provider)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{provider.value.title()} account is already linked"
            )

        # Check if this provider account is linked to another user
        other_linked = self.find_by_provider_user_id(provider, provider_user_id)
        if other_linked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This {provider.value.title()} account is already linked to another user"
            )

        # Create linked account
        linked_account = LinkedAccount(
            user_id=user_id,
            provider=provider.value,  # Store as string value
            provider_user_id=provider_user_id,
            provider_email=provider_email,
        )
        self.session.add(linked_account)
        self.session.commit()
        self.session.refresh(linked_account)

        return linked_account

    def unlink_account(
        self, user_id: UUID, provider: OAuthProvider
    ) -> list[str]:
        """
        Unlink an OAuth account from a user.
        Returns list of remaining linked providers.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        linked = self.get_linked_account_by_provider(user_id, provider)
        if not linked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {provider.value.title()} account linked"
            )

        # Check if user has other login methods
        all_linked = self.get_linked_accounts(user_id)
        has_password = user.hashed_password is not None
        # acc.provider is string, provider is enum
        other_providers = [acc for acc in all_linked if acc.provider != provider.value]

        if not has_password and len(other_providers) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot unlink the last login method. Add a password or link another account first."
            )

        # Delete linked account
        self.session.delete(linked)
        self.session.commit()

        return [acc.provider for acc in other_providers]

    def can_login_with_provider(
        self, provider: OAuthProvider, provider_user_id: str
    ) -> User | None:
        """
        Check if a provider account can be used for login.
        Returns the user if found, None otherwise.
        """
        return self.find_user_by_provider(provider, provider_user_id)

    def find_linked_account_by_email(
        self, provider: OAuthProvider, provider_email: str
    ) -> LinkedAccount | None:
        """Find a linked account by provider and email."""
        statement = select(LinkedAccount).where(
            LinkedAccount.provider == provider.value,
            LinkedAccount.provider_email == provider_email
        )
        return self.session.exec(statement).first()

    def is_provider_email_linked(self, provider_email: str) -> bool:
        """Check if a provider email is already linked to any account."""
        statement = select(LinkedAccount).where(
            LinkedAccount.provider_email == provider_email
        )
        return self.session.exec(statement).first() is not None
