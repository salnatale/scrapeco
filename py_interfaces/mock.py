import os
import json
from typing import Optional,Union, Dict, Any, List
from openai import OpenAI  # The new recommended import from v1.0.0
from pydantic import BaseModel,ValidationError
from models import LinkedInProfile
import random

from dotenv import load_dotenv
load_dotenv(override=True)
# load OPENAI_AI_KEY from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def create_intelligent_mock_profile(**kwargs) -> Dict[str, Any]:
    """
    Uses the OpenAI API (ChatCompletion) to generate a mock LinkedIn profile
    with a structure suitable for parse_raw_profile in LinkedInProfile.
    Returns a dictionary that can be directly passed to LinkedInProfile.parse_raw_profile.

    :param **kwargs: Optional keyword arguments representing the parameters of the LinkedInProfile class.

    :return: Dictionary representing the generated mock LinkedIn profile.
    """
    
    client = OpenAI()
    
    # System message to guide the assistant's style and constraints.
    system_content = '''
    You are a data generator. Produce realistic JSON data for a LinkedIn profile.
        "Match the structure below explicitely, including 'profile_id', 'profile_urn', 'member_urn', 
        'public_id', 'firstName', 'lastName', 'headline', 'summary', 'industryName', 
        'locationName', 'geoCountryName', 'experience', 'education', 'skills', 'urn_id'. 
        Make sure it is valid JSON and it includes at least one experience entry. 
        Use a typical software-engineer-like profile with relevant fields.

    EXAMPLE ENTRY:    
    {
        "profile_id": "67890",
        "profile_urn": "urn:li:fs_profile:ACoAAC67890",
        "member_urn": "urn:li:member:67890",
        "public_id": "lucy-brown-67890",
        "firstName": "Lucy",
        "lastName": "Brown",
        "headline": "Full-Stack Engineer at Microsoft",
        "summary": "Full-stack engineer focused on cloud-native applications, Azure services, and front-end performance optimization.",
        "industryName": "Information Technology and Services",
        "locationName": "Seattle, WA",
        "geoCountryName": "United States",
        "experience": [
            {
                "title": "Full-Stack Engineer",
                "company": {
                    "companyName": "Microsoft",
                    "companyUrn": "urn:li:fs_company:9876",
                    "companyLogoUrl": "https://media.licdn.com/dms/image/C4E0BAQH.png",
                    "employeeCountRange": {"start": 10000, "end": 99999},
                    "industries": ["Software Development", "Cloud Computing"]
                },
                "description": "Develop features across the stack for Azure-based web applications.",
                "locationName": "Redmond, WA",
                "timePeriod": {
                    "startDate": {"year": 2022, "month": 5},
                    "endDate": {"year": 2024, "month": 8}
                },
                "entityUrn": "urn:li:fs_experience:555555"
            },
            {
                "title": "Software Engineer Intern",
                "company": {
                    "companyName": "Amazon",
                    "companyUrn": "urn:li:fs_company:4321",
                    "companyLogoUrl": "https://media.licdn.com/dms/image/C4E0BAQH.png",
                    "employeeCountRange": {"start": 10000, "end": 99999},
                    "industries": ["E-commerce", "Cloud Computing"]
                },
                "description": "Worked on a cross-functional team to optimize internal dashboards for AWS usage analytics.",
                "locationName": "Seattle, WA",
                "timePeriod": {
                    "startDate": {"year": 2021, "month": 6},
                    "endDate": {"year": 2021, "month": 8}
                },
                "entityUrn": "urn:li:fs_experience:444444"
            }
        ],
        "education": [
            {
                "school": {
                    "schoolName": "University of Washington",
                    "schoolUrn": "urn:li:fs_school:67890",
                    "logo_url": null,
                    "active": true
                },
                "degreeName": "Bachelor of Science",
                "fieldOfStudy": "Computer Science",
                "timePeriod": {
                    "startDate": {"year": 2018, "month": 9},
                    "endDate": {"year": 2022, "month": 6}
                },
                "entityUrn": "urn:li:fs_education:22222"
            },
            {
                "school": {
                    "schoolName": "University of Washington",
                    "schoolUrn": "urn:li:fs_school:67890",
                    "logo_url": null,
                    "active": false
                },
                "degreeName": "Master of Science",
                "fieldOfStudy": "Computer Science & Engineering",
                "timePeriod": {
                    "startDate": {"year": 2023, "month": 9},
                    "endDate": {"year": 2025, "month": 6}
                },
                "entityUrn": "urn:li:fs_education:33333"
            }
        ],
        "skills": [
            {"name": "JavaScript"},
            {"name": "Azure"},
            {"name": "React"}
        ],
        "certifications": [
            {
                "name": "Microsoft Certified: Azure Developer Associate",
                "authority": "Microsoft"
            }
        ],
        "languages": [
            {"name": "English"},
            {"name": "Spanish"}
        ],
        "publications": [],
        "honors": [],
        "volunteer": [],
        "projects": [],
        "urn_id": "ACoAAC67890"
    }
    '''

    # We'll just instruct the model to produce a single JSON object. 
    # This is an example prompt; you can get as creative and detailed as you like.
    user_content = "Generate a new random software engineer LinkedIn profile in JSON."
    sys_content_continued = f"Please ensure these arguments are set as the field of the Linkedin Profile, Explicitly. {(kwargs)}"
    
    # Create a Chat Completion request
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[
            {"role": "system", "content": system_content+sys_content_continued},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )

    # The response is a pydantic model. To get the text, we access .choices[0].message.content
    raw_json_str = response.choices[0].message.content.strip()

    try:
        raw_profile = json.loads(raw_json_str)
    except json.JSONDecodeError:
        raise ValueError(
            "OpenAI returned invalid JSON; here's what we got:\n" + raw_json_str
        )
    
    return raw_profile

def propose_next_role_with_completions(
    profile_data: LinkedInProfile,
    role_title: Optional[str] = None,
    company_name: Optional[str] = None,
    description: Optional[str] = None,
    start_year: Optional[int] = None,
    start_month: Optional[int] = None,
    model: str = "gpt-4o",
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Uses the new OpenAI v1.x 'completions' endpoint to append a realistic next role 
    to a LinkedIn-style profile (profile_data), returning the updated dictionary.

    :param profile_data: A dict representing a LinkedIn-style profile 
                         (e.g. from LinkedInProfile.parse_raw_profile(...)).
    :param role_title:   Optional desired job title for the new role.
    :param company_name: Optional name of the next company.
    :param description:  Optional job description for the new role.
    :param start_year:   Optional int for the next role's start year.
    :param start_month:  Optional int for the next role's start month.
    :param model:        The model to use for completions (default 'curie').
    :param temperature:  Temperature for the generation (default 0.7).
    :param api_key:      API key to authenticate with OpenAI. 
                         If None, we use os.environ['OPENAI_API_KEY'].

    :return: Updated profile_data (dict) with the new role appended in 'experience'.
    """

        # Convert a Pydantic model to dict if necessary.
    if isinstance(profile_data, LinkedInProfile):
        # incoporate used aliases
        raw_profile_dict = profile_data.model_dump()  # Pydantic v2 approach
        # If using Pydantic v1, use `profile_data.dict()`
    else:
        raw_profile_dict = profile_data

    # Instantiate an OpenAI client
    client = OpenAI()

    # We'll build a prompt providing the current profile, plus instructions to add a next role.
    # We incorporate optional parameters if provided.
    optional_instructions = []
    if role_title:
        optional_instructions.append(f"Role Title: {role_title}")
    if company_name:
        optional_instructions.append(f"Company Name: {company_name}")
    if description:
        optional_instructions.append(f"Description: {description}")
    if start_year:
        optional_instructions.append(f"Start Year: {start_year}")
    if start_month:
        optional_instructions.append(f"Start Month: {start_month}")

    instructions_block = "\n".join(optional_instructions)

    enforce_alias = """
Use the following JSON structure, including these exact field names (aliases). All keys must match exactly:

TimePeriod:
• "startDate": { "year": number, "month": number }
• "endDate": { "year": number, "month": number }

Company:
• "companyName": string
• "companyUrn": string (optional)
• "companyLogoUrl": string (optional)
• "employeeCountRange": { "start": number, "end": number } (optional)
• "industries": array of strings (optional)

Location:
• "locationName": string (optional)
• "geoLocationName": string (optional)
• "geoUrn": string (optional)
• "region": string (optional)

Experience:
• "title": string
• "company": object with Company fields
• "description": string (optional)
• "location": object with Location fields (optional)
• "timePeriod": object with TimePeriod fields
• "entityUrn": string (optional)

School:
• "schoolName": string
• "schoolUrn": string (optional)
• "logo_url": string (optional)
• "active": boolean (optional)

Education:
• "school": object with School fields
• "degreeName": string (optional)
• "fieldOfStudy": string (optional)
• "timePeriod": object with TimePeriod fields
• "entityUrn": string (optional)

Author:
• "member": object
• "profileUrn": string (optional)

Publication:
• "name": string
• "description": string (optional)
• "authors": array of Author objects

Certification:
• "name": string
• "authority": string (optional)
• "company": object (optional)
• "companyUrn": string (optional)

Honor:
• "title": string
• "description": string (optional)

Skill:
• "name": string

Language:
• "name": string

LinkedInProfile:
• "profile_id": string
• "profile_urn": string
• "member_urn": string (optional)
• "public_id": string (optional)
• "firstName": string
• "lastName": string
• "headline": string (optional)
• "summary": string (optional)
• "industryName": string (optional)
• "industryUrn": string (optional)
• "locationName": string (optional)
• "geoCountryName": string (optional)
• "geoCountryUrn": string (optional)
• "student": boolean (optional)
• "experience": array of Experience objects
• "education": array of Education objects
• "publications": array of Publication objects
• "certifications": array of Certification objects
• "languages": array of Language objects
• "volunteer": array of objects (optional)
• "honors": array of Honor objects
• "projects": array of objects (optional)
• "skills": array of Skill objects
• "urn_id": string

AccountStatus:
• "rate_limit": number
• "remaining_calls": number
• "reset_time": string (ISO datetime)
• "usable": boolean (optional, defaults to true)

APIStatus:
• "last_call": string (ISO datetime)
• "total_calls": number
• "account_statuses": object mapping account ID → AccountStatus

LocalizedContent:
• "text": string

ImageArtifact:
• "fileIdentifyingUrlPathSegment": string
• "expiresAt": number
• "width": number
• "height": number

VectorImage:
• "artifacts": array of ImageArtifact
• "rootUrl": string

CompanyImage:
• "image": object mapping string → VectorImage
• "type": string (optional)
• "cropInfo": object (optional)

CompanyIndustry:
• "localizedName": string
• "entityUrn": string

CompanyPermissions:
• "landingPageAdmin": boolean
• "admin": boolean
• "adAccountHolder": boolean

FollowingInfo:
• "entityUrn": string
• "dashFollowingStateUrn": string
• "following": boolean
• "followingType": string
• "followerCount": number

FundingInvestor:
• "name": object mapping (e.g. { "en": "..." })
• "investorCrunchbaseUrl": string
• "image": object (optional)

FundingRound:
• "investorsCrunchbaseUrl": string
• "leadInvestors": array of FundingInvestor
• "fundingRoundCrunchbaseUrl": string
• "fundingType": string
• "moneyRaised": object (e.g. { "currencyCode": "USD", "amount": "17000000" })
• "numOtherInvestors": number
• "announcedOn": object (e.g. { "year": 2025, "month": 2, "day": 18 })

FundingData:
• "fundingRoundListCrunchbaseUrl": string
• "lastFundingRound": FundingRound
• "companyCrunchbaseUrl": string
• "numFundingRounds": number
• "updatedAt": number

CompanyType:
• "localizedName": string
• "code": string

LinkedInCompany:
• "name": string
• "tagline": string
• "description": string
• "entityUrn": string
• "universalName": string
• "companyPageUrl": string
• "url": string
• "staffingCompany": boolean
• "companyIndustries": array of CompanyIndustry
• "staffCount": number
• "staffCountRange": object { "start": number, "end": number }
• "permissions": CompanyPermissions
• "logo": CompanyImage
• "followingInfo": FollowingInfo
• "fundingData": FundingData (optional)
• "companyType": CompanyType
• "backgroundCoverImage": CompanyImage (optional)

When returning JSON data, ensure all objects and arrays match these aliases/names exactly.
"""
    system_content = f"""
You are a data generator. Below is a JSON object representing a LinkedIn-style profile.
We want you to:
1. Append a NEW role to the "experience" array that represents a realistic next step
   in this person's career.
2. If the user has specified a new role title, company name, description, or start date,
   please incorporate that exactly. Otherwise, invent something plausible.
3. Output a single valid JSON object with the same structure defined below, ensuring usage of correct aliases for field names! , but with
   the new role appended in 'experience'.

Current Profile JSON:
{json.dumps(raw_profile_dict, indent=2)}

should be of the exact form: 
{enforce_alias}

Additional info (may be partially empty):
{instructions_block}

Return ONLY valid JSON. No extra text.
"""
    
    user_content = "generate a new role for this profile."

    # Call the new Completions endpoint
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],     # adjust as needed
        #TODO: Finish and use profile schema from dataschema
        # response_format= linkedin_profile_schema,
        temperature=temperature,
    )

    raw_json_str = response.choices[0].message.content.strip()

    try:
        raw_profile = json.loads(raw_json_str)
    except json.JSONDecodeError:
        raise ValueError(
            "OpenAI returned invalid JSON; here's what we got:\n" + raw_json_str
        )
    try: 
        return LinkedInProfile(**raw_profile)
    except ValidationError as e:
        print(e)
        print(raw_profile)
        raise ValueError("Generated profile does not match the LinkedInProfile schema.")

def llm_filter_profile_list(profiles: List[LinkedInProfile], description: str, p:float) -> List[LinkedInProfile]:
    """
    Filter a list of LinkedInProfile objects based on a description LLM query match.

    :param profiles: List of LinkedInProfile objects.
    :param description: Substring to match in the 'description' field of each profile.

    :return: List of LinkedInProfile objects that contain the description substring.
    """
    # dump profiles to JSON strings
    profile_data = [p.model_dump_json() for p in profiles]
    # format into a single string, with indices delineating each profile
    profile_data_str = "\n".join([f"{i+1}. {p}" for i, p in enumerate(profile_data)])
    # create the LLM query
    # system content
    system_content = f'''
    You are a data filter. You have a list of LinkedIn profiles and a description to match.
    Your task is to filter the profiles based on the description provided. Using your judgment,
    return the profiles that match the description, to a confidence level of {p}.
    Only return the indices of the profiles that match the description, in list format.
    '''
    assistant_content = f'''
    A successful match is defined as a profile where the 'description' field contains the provided description.
    The format of the output, should be a list of indices of the profiles that match the description.
    If there are 10 profiles, and the 1st, 3rd, and 5th profiles match the description, the output should be:
    [1, 3, 5]
    Adhere to this strictly.
    The indices should be 1-indexed.
    This means the first profile should be index 1, not 0, and the last profile should be index N, not N-1.
    Do not return the profiles themselves, only the indices.
    Only return a response in the form of a python list of indices.
    Examples:
    If the description is "software engineer" and the 2nd and 4th profiles match, return [2, 4].
    If no profiles match, return an empty list [].
    If all profiles match, return a list of all indices [1, 2, 3, ...].
    If the confidence level is not met, return an empty list [].
    '''
    user_content = f'''
    Given the following LinkedIn profiles, filter the profiles that match the description:
    {description}
    Here are the profiles:
    {profile_data_str}
    '''
    # create the LLM query
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "developer", "content": system_content},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        temperature=0.7,
    )
    # extract the response
    response_text = response.choices[0].message.content
    # parse the response into a list of indices
    if response_text:
        indices = json.loads(response_text)
    else:
        indices = []
    # filter the profiles based on the indices
    filtered_profiles = [profiles[i-1] for i in indices if 0 < i <= len(profiles)]
    return filtered_profiles

def generate_next_role_for_group(profiles: List[LinkedInProfile], p:float) -> List[LinkedInProfile]:
    """
    Generate a next role for a group of LinkedIn profiles, with probability p.
    """
    bank_of_companies = ["Google", "Microsoft", "Amazon", "Facebook", "Apple", "Netflix", "Tesla", "SpaceX", "Twitter", "LinkedIn", 
                            "Uber", "Airbnb", "Slack", "Dropbox", "Pinterest", "Reddit", "Spotify", "Zoom", "Stripe", "Shopify",
                            "Salesforce", "IBM", "Oracle", "Intel", "Cisco", "HP", "Dell", "VMware", "Adobe", "Nvidia", "Qualcomm",
                            "Alphabet", "IBM", "Sony", "Samsung", "LG", "Nokia", "Huawei", "Tencent", "Alibaba", "Baidu", "JD.com",
                            "TikTok", "Snapchat", "PayPal", "Square", "Robinhood", "Coinbase", "Stripe", "Twilio", "Zendesk", "Atlassian",]
    bank_of_reasons = ["to lead a new team in developing cutting-edge AI technologies",
                        "to spearhead the company's expansion into new markets",
                        "to drive innovation in the field of cloud computing",
                        "to optimize the company's data analytics pipeline",
                        "to build a world-class engineering team",
                        "to create a new product that will revolutionize the industry",
                        "to establish a new research lab focused on machine learning",
                        "to launch a new line of business in the fintech sector",
                        "to oversee the development of a new mobile app",
                        "to architect the company's transition to a microservices architecture",
                        "to scale the company's infrastructure to support millions of users",
                        "to design and implement a new cybersecurity strategy",
                        "to lead the company's efforts in sustainability and renewable energy",
                        "to develop a new marketing campaign to attract top talent",
                        "to manage the company's strategic partnerships and alliances",
                        "to drive the company's digital transformation initiatives",
                        "to create a new customer experience platform",
                        "to establish a new center of excellence for data science",
                        "to lead the company's efforts in corporate social responsibility",
                        "to oversee the company's compliance and risk management programs"]
    list = List[LinkedInProfile]
    for profile in profiles:
        if random.random() < p:
            role_title = profile.experience[-1].title
            company_name = random.choice(bank_of_companies)
            description = random.choice(bank_of_reasons)
            start_year = random.randint(2022, 2025)
            start_month = random.randint(1, 12)
            #TODO: finish propose_next_role_with_completions and test within generate_next_role_for_group
            new_role = propose_next_role_with_completions(profile, role_title, company_name, description, start_year, start_month)
            list.append(new_role)
        else:
            list.append(profile)
    return list
