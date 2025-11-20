"""
Database Schemas for BirthdayDeals

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase of the class name.

Countries served: NL (Nederland), AE (Dubai), BH (Bahrein)
All country-bound documents include a country_code field with one of {"NL","AE","BH"}.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr, HttpUrl

CountryCode = Literal["NL", "AE", "BH"]

class AppUser(BaseModel):
    """
    Users collection schema
    Collection: "appuser"
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password_hash: str = Field(..., description="Password hash")
    role: Literal["user", "company", "admin"] = Field("user")
    country_code: CountryCode = Field(..., description="Country for region-lock")
    referral_code: Optional[str] = Field(None, description="User's referral code")
    referred_by: Optional[str] = Field(None, description="Referral code of the inviter")
    is_active: bool = Field(True)

class Company(BaseModel):
    """
    Companies collection schema
    Collection: "company"
    """
    name: str
    email: EmailStr
    country_code: CountryCode
    phone: Optional[str] = None
    website: Optional[str] = None
    verified: bool = False
    owner_user_id: Optional[str] = None

class Deal(BaseModel):
    """
    Deals collection schema
    Collection: "deal"
    """
    title: str
    description: str
    country_code: CountryCode
    company_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    is_active: bool = True

class Banner(BaseModel):
    """
    Banners collection schema
    Collection: "banner"
    """
    title: str
    image_url: HttpUrl
    link_url: Optional[HttpUrl] = None
    country_code: CountryCode
    is_active: bool = True
    position: Optional[int] = Field(0, description="Order on the landing page")

class Application(BaseModel):
    """
    Work/Internship applications
    Collection: "application"
    """
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    country_code: CountryCode
    application_type: Literal["werk", "stage"]
    message: Optional[str] = None
    source: Optional[str] = Field(None, description="Where did the applicant come from")

# Note: Additional schemas (sessions, audits, etc.) will be added in later blocks.
