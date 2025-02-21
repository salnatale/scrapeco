from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


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