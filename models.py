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
    publications: List[Publication] = []
    certifications: List[Certification] = []
    languages: List[Language] = []
    volunteer: List[Dict[str, Any]] = []
    honors: List[Honor] = []
    projects: List[Dict[str, Any]] = []
    skills: List[Skill] = []
    
    urn_id: str = Field(..., alias="urn_id")

    class Config:
        populate_by_name = True
        
    def parse_raw_profile(cls, raw_data: Dict[str, Any]) -> "LinkedInProfile":
        """
        Factory method to parse a raw LinkedIn profile JSON into a structured model
        """
        # Extract and normalize experiences
        experiences = []
        for exp_data in raw_data.get("experience", []):
            # Create Location object if location data exists
            location = None
            if "locationName" in exp_data or "geoLocationName" in exp_data:
                location = Location(
                    name=exp_data.get("locationName"),
                    geo_name=exp_data.get("geoLocationName"),
                    geo_urn=exp_data.get("geoUrn"),
                    region=exp_data.get("region")
                )
            
            # Create Company object
            company_data = exp_data.get("company", {})
            if not company_data and "companyName" in exp_data:
                company = Company(
                    name=exp_data["companyName"],
                    urn=exp_data.get("companyUrn"),
                    logo_url=exp_data.get("companyLogoUrl")
                )
            else:
                company = Company(
                    name=exp_data["companyName"],
                    urn=exp_data.get("companyUrn"),
                    logo_url=exp_data.get("companyLogoUrl"),
                    employee_count_range=company_data.get("employeeCountRange"),
                    industries=company_data.get("industries")
                )
            
            # Create Experience object
            experiences.append(Experience(
                title=exp_data["title"],
                company=company,
                description=exp_data.get("description"),
                location=location,
                time_period=TimePeriod(**exp_data["timePeriod"]),
                entity_urn=exp_data.get("entityUrn")
            ))
        
        # Process other sections similarly...
        
        return cls(
            profile_id=raw_data["profile_id"],
            profile_urn=raw_data["profile_urn"],
            member_urn=raw_data.get("member_urn"),
            public_id=raw_data.get("public_id"),
            first_name=raw_data["firstName"],
            last_name=raw_data["lastName"],
            headline=raw_data.get("headline"),
            summary=raw_data.get("summary"),
            industry_name=raw_data.get("industryName"),
            location_name=raw_data.get("locationName"),
            geo_country_name=raw_data.get("geoCountryName"),
            experience=experiences,
            # Process other sections accordingly
            urn_id=raw_data["urn_id"]
        )
    
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
        # 1. Parse company industries (safe fallback to empty list)
        industries_data = raw_data.get("companyIndustries", [])
        company_industries = []
        for ind in industries_data:
            # Each industry should match CompanyIndustry fields
            # If any required field is missing, you might handle/skip it here
            try:
                ci = CompanyIndustry(**ind)
                company_industries.append(ci)
            except ValidationError:
                # Optionally log or handle the validation error
                pass

        # 2. Parse permissions (all fields are booleans, default to False)
        permissions_data = {
            "landingPageAdmin": raw_data.get("permissions", {}).get("landingPageAdmin", False),
            "admin": raw_data.get("permissions", {}).get("admin", False),
            "adAccountHolder": raw_data.get("permissions", {}).get("adAccountHolder", False),
        }
        try:
            permissions = CompanyPermissions(**permissions_data)
        except ValidationError:
            # If something is wrong, fallback to a default
            permissions = CompanyPermissions(landing_page_admin=False, admin=False, ad_account_holder=False)

        # 3. Parse following info
        following_info_data = {
            "entityUrn": raw_data.get("followingInfo", {}).get("entityUrn", ""),
            "dashFollowingStateUrn": raw_data.get("followingInfo", {}).get("dashFollowingStateUrn", ""),
            "following": raw_data.get("followingInfo", {}).get("following", False),
            "followingType": raw_data.get("followingInfo", {}).get("followingType", ""),
            "followerCount": raw_data.get("followingInfo", {}).get("followerCount", 0),
        }
        try:
            following_info = FollowingInfo(**following_info_data)
        except ValidationError:
            # Fallback to a default
            following_info = FollowingInfo(
                entity_urn="", dash_following_state_urn="", following=False, following_type="", follower_count=0
            )

        # 4. Parse funding data (if present)
        funding_data: Optional[FundingData] = None
        if "fundingData" in raw_data and raw_data["fundingData"]:
            fd_raw = raw_data["fundingData"]
            # Parse lastFundingRound safely
            last_funding_round_data = fd_raw.get("lastFundingRound", {})
            if last_funding_round_data:
                # Parse lead investors
                lead_investors_data = last_funding_round_data.get("leadInvestors", [])
                lead_investors = []
                for inv_data in lead_investors_data:
                    try:
                        lead_investors.append(FundingInvestor(**inv_data))
                    except ValidationError:
                        pass
                # Update with parsed lead investors
                last_funding_round_data["leadInvestors"] = lead_investors

                # Attempt to build the FundingRound
                try:
                    last_funding_round = FundingRound(**last_funding_round_data)
                    # Put it back into the overall funding dict
                    fd_raw["lastFundingRound"] = last_funding_round
                except ValidationError:
                    fd_raw["lastFundingRound"] = None

            try:
                funding_data = FundingData(**fd_raw)
            except ValidationError:
                funding_data = None

        # 5. Parse company type
        company_type_raw = raw_data.get("companyType", {})
        try:
            company_type = CompanyType(**company_type_raw)
        except ValidationError:
            # Fallback if required fields are missing
            company_type = CompanyType(localized_name="", code="")

        # 6. Parse company logo (CompanyImage) safely
        logo_data = raw_data.get("logo", {})
        # Safely parse the nested image structure
        image_dict_parsed = {}
        if "image" in logo_data:
            for key, vector_dict in logo_data["image"].items():
                if not isinstance(vector_dict, dict):
                    continue
                artifacts_raw = vector_dict.get("artifacts", [])
                artifacts_parsed = []
                for art in artifacts_raw:
                    try:
                        artifacts_parsed.append(ImageArtifact(**art))
                    except ValidationError:
                        pass
                # Build the VectorImage
                try:
                    image_dict_parsed[key] = VectorImage(
                        artifacts=artifacts_parsed,
                        root_url=vector_dict.get("rootUrl", "")
                    )
                except ValidationError:
                    image_dict_parsed[key] = None
        # Update logo_data with the safely parsed image structure
        logo_data["image"] = image_dict_parsed if image_dict_parsed else {}

        try:
            company_logo = CompanyImage(**logo_data)
        except ValidationError:
            # Fallback if something is invalid
            company_logo = CompanyImage(image={})

        # 7. Parse background cover image (CompanyImage) safely
        background_cover_image_data = raw_data.get("backgroundCoverImage", {})
        bg_image_parsed = {}
        if "image" in background_cover_image_data:
            for key, vector_dict in background_cover_image_data["image"].items():
                if not isinstance(vector_dict, dict):
                    continue
                artifacts_raw = vector_dict.get("artifacts", [])
                artifacts_parsed = []
                for art in artifacts_raw:
                    try:
                        artifacts_parsed.append(ImageArtifact(**art))
                    except ValidationError:
                        pass
                try:
                    bg_image_parsed[key] = VectorImage(
                        artifacts=artifacts_parsed,
                        root_url=vector_dict.get("rootUrl", "")
                    )
                except ValidationError:
                    bg_image_parsed[key] = None

        background_cover_image_data["image"] = bg_image_parsed if bg_image_parsed else {}
        try:
            background_cover_image = CompanyImage(**background_cover_image_data)
        except ValidationError:
            background_cover_image = None

        # 8. Construct the LinkedInCompany object
        return cls(
            name=raw_data.get("name", ""),
            tagline=raw_data.get("tagline", ""),
            description=raw_data.get("description", ""),
            entity_urn=raw_data.get("entityUrn", ""),
            universal_name=raw_data.get("universalName", ""),
            company_page_url=raw_data.get("companyPageUrl", ""),
            url=raw_data.get("url", ""),
            staffing_company=raw_data.get("staffingCompany", False),
            company_industries=company_industries,
            staff_count=raw_data.get("staffCount", 0),
            staff_count_range=raw_data.get("staffCountRange", {}),
            permissions=permissions,
            logo=company_logo,
            following_info=following_info,
            funding_data=funding_data,
            company_type=company_type,
            background_cover_image=background_cover_image,
        )

    # Attach it to the Pydantic model via a classmethod, for example:
    # class LinkedInCompany(BaseModel):
    #     ...
    #     @classmethod
    #     def parse_raw_model(cls, raw_data: Dict[str, Any]) -> "LinkedInCompany":
    #         return parse_raw_model(cls, raw_data)
