from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class TimePeriod(BaseModel):
    """Time period with start and end dates"""

    start_date: Optional[dict[str, Optional[int]]] = None
    end_date: Optional[dict[str, Optional[int]]] = None


class Company(BaseModel):
    """Company entity for tracking investments and employee transitions"""

    name: str
    urn: Optional[str] = None
    employee_count_range: Optional[dict[str, Optional[int]]] = None
    industries: Optional[list[str]] = None

    # VC-specific attributes
    funding_stage: Optional[str] = None  # "seed", "series_a", "series_b", etc.
    valuation: Optional[float] = None
    exit_status: Optional[str] = None  # "private", "ipo", "acquired", "closed"
    founded_year: Optional[int] = None


class Location(BaseModel):
    """Geographic location"""

    name: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class Experience(BaseModel):
    """Work experience at a company"""

    title: str
    company: Company
    description: Optional[str] = None
    location: Optional[Location] = None
    time_period: TimePeriod
    seniority_level: Optional[str] = None  # "junior", "mid", "senior", "executive"


class School(BaseModel):
    """Educational institution"""

    name: str
    urn: Optional[str] = None
    ranking: Optional[int] = None  # University ranking for network effects


class Education(BaseModel):
    """Educational background"""

    school: School
    degree_name: Optional[str] = None
    field_of_study: Optional[str] = None
    time_period: TimePeriod


class Skill(BaseModel):
    """Professional skill"""

    name: str
    category: Optional[str] = None  # "technical", "management", "domain"


class Employee(BaseModel):
    """Employee/Professional profile (formerly LinkedInProfile)"""

    profile_id: str
    profile_urn: str
    first_name: str
    last_name: str
    headline: Optional[str] = None
    summary: Optional[str] = None
    industry_name: Optional[str] = None
    location_name: Optional[str] = None

    experience: list[Experience] = []
    education: list[Education] = []
    skills: list[Skill] = []

    # Analytics attributes
    career_progression_score: Optional[float] = None
    network_influence: Optional[float] = None


class TransitionEvent(BaseModel):
    """Career transition event for tracking talent flow"""

    profile_urn: str
    from_company_urn: str
    to_company_urn: str
    transition_date: Optional[datetime | str]
    transition_type: Optional[Literal["company_change", "promotion"]]
    old_title: Optional[str]
    new_title: Optional[str]
    location_change: Optional[bool] = None
    tenure_days: Optional[int] = None
    seniority_change: Optional[int] = None  # -1 (down), 0 (lateral), 1 (up)


# VC-Specific Models


class Fund(BaseModel):
    """Venture capital fund"""

    id: str
    name: str
    aum: Optional[float] = None  # Assets under management
    vintage: int  # Fund year
    focus_areas: list[str] = []  # ["ai", "fintech", "healthcare"]
    stage_focus: list[str] = []  # ["seed", "series_a", "growth"]
    geographic_focus: list[str] = []
    status: Optional[str] = "active"  # "active", "closed", "fundraising"


class Investment(BaseModel):
    """Investment relationship between fund and company"""

    id: str
    fund_id: str
    company_id: str
    amount: Optional[float] = None
    round_type: str  # "seed", "series_a", etc.
    date: datetime
    valuation_pre: Optional[float] = None
    valuation_post: Optional[float] = None
    ownership_percentage: Optional[float] = None


class Exit(BaseModel):
    """Company exit event"""

    id: str
    company_id: str
    exit_type: Literal["IPO", "Acquisition", "Shutdown", "Buyback"]
    exit_date: datetime
    valuation: Optional[float] = None
    acquirer_id: Optional[str] = None  # If acquisition
    multiple: Optional[float] = None  # Exit value / total invested


class Investor(BaseModel):
    """Individual investor profile"""

    id: str
    name: str
    title: Optional[str] = None
    fund_id: Optional[str] = None
    investment_focus: list[str] = []
    portfolio_companies: list[str] = []
    successful_exits: int = 0
    total_investments: int = 0


# API Status Models (simplified from original)


class APIStatus(BaseModel):
    """API usage tracking"""

    last_call: datetime
    total_calls: int
    remaining_calls: int
    reset_time: datetime
