from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Type, TypeVar
from datetime import datetime
from pydantic import ValidationError


class TimePeriod(BaseModel):
    start_date: Optional[Dict[str, int]] = Field(None, alias="startDate")
    end_date: Optional[Dict[str, int]] = Field(None, alias="endDate")

    class Config:
        populate_by_name = True


class Company(BaseModel):
    name: str = Field(..., alias="companyName")
    urn: Optional[str] = Field(None, alias="companyUrn")
    logo_url: Optional[str] = Field(None, alias="companyLogoUrl")
    employee_count_range: Optional[Dict[str, int]] = Field(None, alias="employeeCountRange")
    industries: Optional[List[str]] = None

    class Config:
        populate_by_name = True


class Location(BaseModel):
    name: Optional[str] = Field(None, alias="locationName")
    geo_name: Optional[str] = Field(None, alias="geoLocationName")
    geo_urn: Optional[str] = Field(None, alias="geoUrn")
    region: Optional[str] = None

    class Config:
        populate_by_name = True


class Experience(BaseModel):
    title: str
    company: Company
    description: Optional[str] = None
    location: Optional[Location] = None
    time_period: TimePeriod = Field(..., alias="timePeriod")
    entity_urn: Optional[str] = Field(None, alias="entityUrn")

    class Config:
        populate_by_name = True


class School(BaseModel):
    name: str = Field(..., alias="schoolName")
    urn: Optional[str] = Field(None, alias="schoolUrn")
    logo_url: Optional[str] = None
    active: Optional[bool] = None

    class Config:
        populate_by_name = True


class Education(BaseModel):
    school: School
    degree_name: Optional[str] = Field(None, alias="degreeName")
    field_of_study: Optional[str] = Field(None, alias="fieldOfStudy")
    time_period: TimePeriod = Field(..., alias="timePeriod")
    entity_urn: Optional[str] = Field(None, alias="entityUrn")

    class Config:
        populate_by_name = True


class Author(BaseModel):
    member: Dict[str, Any]
    profile_urn: Optional[str] = Field(None, alias="profileUrn")

    class Config:
        populate_by_name = True


class Publication(BaseModel):
    name: str
    description: Optional[str] = None
    authors: List[Author]

    class Config:
        populate_by_name = True


class Certification(BaseModel):
    name: str
    authority: Optional[str] = None
    company: Optional[Dict[str, Any]] = None
    company_urn: Optional[str] = Field(None, alias="companyUrn")

    class Config:
        populate_by_name = True


class Honor(BaseModel):
    title: str
    description: Optional[str] = None

    class Config:
        populate_by_name = True


class Skill(BaseModel):
    name: str

    class Config:
        populate_by_name = True


class Language(BaseModel):
    name: str

    class Config:
        populate_by_name = True


class LinkedInProfile(BaseModel):
    profile_id: str = Field(..., alias="profile_id")
    profile_urn: str = Field(..., alias="profile_urn")
    member_urn: Optional[str] = Field(None, alias="member_urn")
    public_id: Optional[str] = Field(None, alias="public_id")
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    headline: Optional[str] = None
    summary: Optional[str] = None
    industry_name: Optional[str] = Field(None, alias="industryName")
    industry_urn: Optional[str] = Field(None, alias="industryUrn")
    location_name: Optional[str] = Field(None, alias="locationName")
    geo_country_name: Optional[str] = Field(None, alias="geoCountryName")
    geo_country_urn: Optional[str] = Field(None, alias="geoCountryUrn")
    is_student: Optional[bool] = Field(None, alias="student")
    
    experience: List[Experience] = []
    education: List[Education] = []
    # publications: List[Publication] = []
    # certifications: List[Certification] = []
    # languages: List[Language] = []
    # volunteer: List[Dict[str, Any]] = []
    # honors: List[Honor] = []
    projects: List[Dict[str, Any]] = []
    skills: List[Skill] = []
    
    urn_id: str = Field(..., alias="urn_id")

    class Config:
        populate_by_name = True
    
    def parse_raw_profile(cls, raw_data: Dict[str, Any]) -> "LinkedInProfile":
        """
        Factory method to parse a raw LinkedIn profile JSON into this structured model,
        using Pydantic's auto-nesting where possible.
        """
        return cls(**raw_data)
    
    @classmethod
    def identify_experience_change(cls, old_profile: "LinkedInProfile", new_profile: "LinkedInProfile") -> tuple["LinkedInProfile",List[Experience],datetime]:
        """
        if there is an experience change, return the necessary information to denote the change. 
        profile: LinkedInProfile, 
        # old_experience: Experience, 
        # new_experience: Experience, 
        # transition_date: datetime,
        # identify all the above info
        """
        # ensure profiles are the same, in important fields
    #         profile_id: str = Field(..., alias="profile_id")
    # profile_urn: str = Field(..., alias="profile_urn")
    # member_urn: Optional[str] = Field(None, alias="member_urn")
    # public_id: Optional[str] = Field(None, alias="public_id")
    # first_name: str = Field(..., alias="firstName")
    # last_name: str = Field(..., alias="lastName")
        try: 
            assert(
            old_profile.profile_id == new_profile.profile_id and
            old_profile.profile_urn == new_profile.profile_urn and
            old_profile.member_urn == new_profile.member_urn and
            old_profile.public_id == new_profile.public_id and
            old_profile.first_name == new_profile.first_name and
            old_profile.last_name == new_profile.last_name
        )
        except AssertionError:
            print("exception: profiles are not the same")
            return (None, None, None)

        old_curr_experience = old_profile.experience[-1]
        new_curr_experience = new_profile.experience[-1]
        if old_curr_experience != new_curr_experience:
            # return all necessary info from above
            return (new_profile,[old_curr_experience, new_curr_experience], datetime.now())
    
# api status models 
# per account class, containing rate limit, remaining calls, reset time
class AccountStatus(BaseModel):
    rate_limit: int
    remaining_calls: int
    reset_time: datetime
    usable: bool = True

    class Config:
        populate_by_name = True

class APIStatus(BaseModel):
    # last call generally, and per account : last call, rate limit, remaining calls, reset time. 
    last_call: datetime
    total_calls: int
    account_statuses: Dict[str, AccountStatus]
    class Config:
        populate_by_name = True

# ______________________________________________________
# Pydantic company models
class LocalizedContent(BaseModel):
    text: str

class ImageArtifact(BaseModel):
    width: int
    height: int
    file_identifying_url_segment: str = Field(..., alias="fileIdentifyingUrlPathSegment")
    expires_at: int = Field(..., alias="expiresAt")

class VectorImage(BaseModel):
    artifacts: List[ImageArtifact]
    root_url: str = Field(..., alias="rootUrl")

class CompanyImage(BaseModel):
    image: Dict[str, VectorImage]
    type: Optional[str] = None
    crop_info: Optional[Dict[str, Any]] = Field(None, alias="cropInfo")

class CompanyIndustry(BaseModel):
    localized_name: str = Field(..., alias="localizedName")
    entity_urn: str = Field(..., alias="entityUrn")

class CompanyPermissions(BaseModel):
    landing_page_admin: bool = Field(..., alias="landingPageAdmin")
    admin: bool
    ad_account_holder: bool = Field(..., alias="adAccountHolder")

class FollowingInfo(BaseModel):
    entity_urn: str = Field(..., alias="entityUrn")
    dash_following_state_urn: str = Field(..., alias="dashFollowingStateUrn")
    following: bool
    following_type: str = Field(..., alias="followingType")
    follower_count: int = Field(..., alias="followerCount")

class FundingInvestor(BaseModel):
    name: Dict[str, str]
    investor_crunchbase_url: str = Field(..., alias="investorCrunchbaseUrl")
    image: Optional[Dict[str, List[Dict[str, str]]]]

class FundingRound(BaseModel):
    investors_crunchbase_url: str = Field(..., alias="investorsCrunchbaseUrl")
    lead_investors: List[FundingInvestor] = Field(..., alias="leadInvestors")
    funding_round_crunchbase_url: str = Field(..., alias="fundingRoundCrunchbaseUrl")
    funding_type: str = Field(..., alias="fundingType")
    money_raised: Dict[str, Any] = Field(..., alias="moneyRaised")
    num_other_investors: int = Field(..., alias="numOtherInvestors")
    announced_on: Dict[str, int] = Field(..., alias="announcedOn")

class FundingData(BaseModel):
    funding_round_list_crunchbase_url: str = Field(..., alias="fundingRoundListCrunchbaseUrl")
    last_funding_round: FundingRound = Field(..., alias="lastFundingRound")
    company_crunchbase_url: str = Field(..., alias="companyCrunchbaseUrl")
    num_funding_rounds: int = Field(..., alias="numFundingRounds")
    updated_at: int = Field(..., alias="updatedAt")

class CompanyType(BaseModel):
    localized_name: str = Field(..., alias="localizedName")
    code: str

class LinkedInCompany(BaseModel):
    name: str
    tagline: str
    description: str
    entity_urn: str = Field(..., alias="entityUrn")
    universal_name: str = Field(..., alias="universalName")
    company_page_url: str = Field(..., alias="companyPageUrl")
    url: str
    staffing_company: bool = Field(..., alias="staffingCompany")
    company_industries: List[CompanyIndustry] = Field(..., alias="companyIndustries")
    staff_count: int = Field(..., alias="staffCount")
    staff_count_range: Dict[str, int] = Field(..., alias="staffCountRange")
    permissions: CompanyPermissions
    logo: CompanyImage
    following_info: FollowingInfo = Field(..., alias="followingInfo")
    funding_data: Optional[FundingData] = Field(None, alias="fundingData")
    company_type: CompanyType = Field(..., alias="companyType")
    background_cover_image: Optional[CompanyImage] = Field(None, alias="backgroundCoverImage")
    
    class Config:
        populate_by_name = True

    @classmethod
    def parse_raw_model(cls, raw_data: Dict[str, Any]) -> "LinkedInCompany":
        """
        Factory method to parse a raw LinkedIn company JSON into a structured LinkedInCompany model,
        using safer lookups with .get() to handle missing fields.
        """
        return cls( **raw_data)

    # Attach it to the Pydantic model via a classmethod, for example:
    # class LinkedInCompany(BaseModel):
    #     ...
    #     @classmethod
    #     def parse_raw_model(cls, raw_data: Dict[str, Any]) -> "LinkedInCompany":
    #         return parse_raw_model(cls, raw_data)
