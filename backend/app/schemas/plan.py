from uuid import UUID
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel
from pydantic import field_validator, model_validator


class PlanBase(SQLModel):
    """Base schema for Plan"""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[int] = None
    yearly_discount_percentage: Optional[float] = None  # Discount % for yearly (0-100)
    currency: Optional[str] = "VND"
    monthly_credits: Optional[int] = None
    additional_credit_price: Optional[int] = None  # Price to buy 100 additional credits
    available_project: Optional[int] = None
    is_active: Optional[bool] = True
    tier: Optional[str] = "pay"  # 'free' | 'pay'
    sort_index: Optional[int] = 0
    is_featured: Optional[bool] = False
    is_custom_price: Optional[bool] = False
    features_text: Optional[str] = None

    @field_validator('monthly_price', 'additional_credit_price')
    @classmethod
    def validate_prices(cls, v: Optional[int]) -> Optional[int]:
        """Validate that prices are non-negative"""
        if v is not None and v < 0:
            raise ValueError('Price must be greater than or equal to 0')
        return v

    @field_validator('yearly_discount_percentage')
    @classmethod
    def validate_discount(cls, v: Optional[float]) -> Optional[float]:
        """Validate that discount percentage is between 0 and 100"""
        if v is not None:
            if v < 0 or v > 100:
                raise ValueError('Discount percentage must be between 0 and 100')
        return v

    @field_validator('monthly_credits', 'sort_index')
    @classmethod
    def validate_non_negative_integers(cls, v: Optional[int]) -> Optional[int]:
        """Validate that counts are non-negative"""
        if v is not None and v < 0:
            raise ValueError('Value must be greater than or equal to 0')
        return v

    @field_validator('available_project')
    @classmethod
    def validate_available_project(cls, v: Optional[int]) -> Optional[int]:
        """Validate available_project (-1 for unlimited, >= 0 for limited)"""
        if v is not None and v < -1:
            raise ValueError('available_project must be -1 (unlimited) or >= 0')
        return v


class PlanCreate(PlanBase):
    """Schema for creating a new plan"""
    code: str
    name: str

    @model_validator(mode='after')
    def validate_plan(self):
        """Validate plan pricing logic"""
        # Check that at least monthly_price is provided for non-custom plans
        if not self.is_custom_price and not self.monthly_price:
            raise ValueError("monthly_price must be provided for non-custom plans")

        return self


class PlanUpdate(SQLModel):
    """Schema for updating an existing plan (all fields optional)"""
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    monthly_price: Optional[int] = None
    yearly_discount_percentage: Optional[float] = None
    currency: Optional[str] = None
    monthly_credits: Optional[int] = None
    additional_credit_price: Optional[int] = None
    available_project: Optional[int] = None
    is_active: Optional[bool] = None
    tier: Optional[str] = None
    sort_index: Optional[int] = None
    is_featured: Optional[bool] = None
    is_custom_price: Optional[bool] = None
    features_text: Optional[str] = None

    @field_validator('monthly_price', 'additional_credit_price')
    @classmethod
    def validate_prices(cls, v: Optional[int]) -> Optional[int]:
        """Validate that prices are non-negative"""
        if v is not None and v < 0:
            raise ValueError('Price must be greater than or equal to 0')
        return v

    @field_validator('yearly_discount_percentage')
    @classmethod
    def validate_discount(cls, v: Optional[float]) -> Optional[float]:
        """Validate that discount percentage is between 0 and 100"""
        if v is not None:
            if v < 0 or v > 100:
                raise ValueError('Discount percentage must be between 0 and 100')
        return v

    @field_validator('monthly_credits', 'sort_index')
    @classmethod
    def validate_non_negative_integers(cls, v: Optional[int]) -> Optional[int]:
        """Validate that counts are non-negative"""
        if v is not None and v < 0:
            raise ValueError('Value must be greater than or equal to 0')
        return v

    @field_validator('available_project')
    @classmethod
    def validate_available_project(cls, v: Optional[int]) -> Optional[int]:
        """Validate available_project (-1 for unlimited, >= 0 for limited)"""
        if v is not None and v < -1:
            raise ValueError('available_project must be -1 (unlimited) or >= 0')
        return v


class PlanPublic(PlanBase):
    """Schema for public plan response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    yearly_price: Optional[int] = None  # Computed from monthly_price and yearly_discount_percentage


class PlansPublic(SQLModel):
    """Schema for paginated plans response"""
    data: list[PlanPublic]
    count: int
