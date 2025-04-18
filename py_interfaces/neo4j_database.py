import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

# Import your existing models
from models import (
    LinkedInProfile, LinkedInCompany, Experience, 
    Company, TimePeriod, Location, School, Education, Skill, TransitionEvent
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

# Neo4j connection settings
#TODO: Set up neo4j database outside of the code
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")

# TODO: GO through and test the Neo4jDatabase and Neo4jProfileAnalyzer queries on
class Neo4jDatabase:
    """
    Handles interactions with Neo4j graph database for LinkedIn profile data.
    """
    
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        """
        Initialize the Neo4j database connection.
        
        Args:
            uri: Neo4j database URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.connect()
    
    def connect(self) -> bool:
        """
        Establish connection to Neo4j database.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connection
            self.driver.verify_connectivity()
            print(f"Successfully connected to Neo4j database at {self.uri}")
            return True
        except (ServiceUnavailable, AuthError) as e:
            print(f"Failed to connect to Neo4j database: {e}")
            self.driver = None
            return False
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            print("Neo4j connection closed")

    def _run_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Run a Cypher query on the Neo4j database.
        
        Args:
            query: Cypher query string
            params: Query parameters
            
        Returns:
            List of query results as dictionaries
        """
        if not self.driver:
            print("No active connection to Neo4j database")
            return []
        
        with self.driver.session() as session:
            try:
                result = session.run(query, params or {})
                return [record.data() for record in result]
            except Exception as e:
                print(f"Error executing Neo4j query: {e}")
                print(f"Query: {query}")
                print(f"Params: {params}")
                return []
    def setup_constraints(self):
        """Set up necessary constraints and indexes for performance."""
        
        # Create constraints to ensure uniqueness where needed
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Profile) REQUIRE p.urn IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.urn IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:School) REQUIRE s.urn IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (p:Profile) ON (p.profileId)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Profile) ON (p.firstName, p.lastName)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Experience) ON (e.title)"
        ]
        
        for constraint in constraints:
            self._run_query(constraint)
        
        print("Neo4j constraints and indexes created successfully")
    
    def store_profile(self, profile: LinkedInProfile):
        """
        Store a LinkedIn profile in the Neo4j database.
        
        Args:
            profile: LinkedInProfile model instance
        """
        # Convert Pydantic model to dict if necessary
        profile_data = profile.model_dump() if hasattr(profile, 'model_dump') else profile
        
        # Create Profile node
        create_profile_query = """
        MERGE (p:Profile {urn: $urn})
        ON CREATE SET 
            p.profileId = $profileId,
            p.firstName = $firstName,
            p.lastName = $lastName,
            p.headline = $headline,
            p.summary = $summary,
            p.locationName = $locationName,
            p.industryName = $industryName,
            p.publicId = $publicId,
            p.createdAt = datetime()
        ON MATCH SET
            p.firstName = $firstName,
            p.lastName = $lastName,
            p.headline = $headline,
            p.summary = $summary,
            p.locationName = $locationName,
            p.industryName = $industryName,
            p.updatedAt = datetime()
        RETURN p
        """
        
        self._run_query(create_profile_query, {
            "urn": profile_data["profile_urn"],
            "profileId": profile_data["profile_id"],
            "firstName": profile_data["first_name"],
            "lastName": profile_data["last_name"],
            "headline": profile_data.get("headline"),
            "summary": profile_data.get("summary"),
            "locationName": profile_data.get("location_name"),
            "industryName": profile_data.get("industry_name"),
            "publicId": profile_data.get("public_id")
        })
        
        # helper methods to process specific profile data

        # Process skills
        if "skills" in profile_data and profile_data["skills"]:
            self.store_skills(profile_data["profile_urn"], profile_data["skills"])
        
        # Process education
        if "education" in profile_data and profile_data["education"]:
            for edu in profile_data["education"]:
                self.store_education(profile_data["profile_urn"], edu)
        
        # Process experience
        if "experience" in profile_data and profile_data["experience"]:
            for exp in profile_data["experience"]:
                self.store_experience(profile_data["profile_urn"], exp)
                
    def store_skills(self, profile_urn: str, skills: List[Dict[str, str]]):
        """
        Store skills for a profile and create relationships.
        
        Args:
            profile_urn: Profile URN
            skills: List of skill dictionaries
        """
        for skill in skills:
            skill_query = """
            MATCH (p:Profile {urn: $profileUrn})
            MERGE (s:Skill {name: $skillName})
            MERGE (p)-[r:HAS_SKILL]->(s)
            RETURN s
            """
            
            self._run_query(skill_query, {
                "profileUrn": profile_urn,
                "skillName": skill["name"]
            })
    
    def store_education(self, profile_urn: str, education: Dict[str, Any]):
        """
        Store education information and create school relationships.
        
        Args:
            profile_urn: Profile URN
            education: Education dictionary
        """
        # Extract data
        school = education["school"]
        school_urn = school.get("urn") or f"urn:li:school:{school['name'].replace(' ', '').lower()}"
        
        # Create School node
        school_query = """
        MERGE (s:School {urn: $schoolUrn})
        ON CREATE SET
            s.name = $schoolName,
            s.active = $active
        ON MATCH SET
            s.name = $schoolName,
            s.active = $active
        
        WITH s
        
        MATCH (p:Profile {urn: $profileUrn})
        MERGE (p)-[r:ATTENDED]->(s)
        ON CREATE SET
            r.degreeName = $degreeName,
            r.fieldOfStudy = $fieldOfStudy,
            r.startYear = $startYear,
            r.startMonth = $startMonth,
            r.endYear = $endYear,
            r.endMonth = $endMonth
        
        RETURN s, r, p
        """
        
        time_period = education["time_period"]
        start_date = time_period.get("start_date", {}) or {}
        end_date = time_period.get("end_date", {}) or {}
        
        self._run_query(school_query, {
            "schoolUrn": school_urn,
            "schoolName": school["name"],
            "active": school.get("active", True),
            "profileUrn": profile_urn,
            "degreeName": education.get("degree_name"),
            "fieldOfStudy": education.get("field_of_study"),
            "startYear": start_date.get("year"),
            "startMonth": start_date.get("month"),
            "endYear": end_date.get("year"),
            "endMonth": end_date.get("month")
        })
    
    def store_company(self, company: Union[LinkedInCompany, Dict[str, Any]]):
        """
        Store a company in the Neo4j database.
        
        Args:
            company: LinkedInCompany model instance or dictionary
        """
        # Convert Pydantic model to dict if necessary
        company_data = company.model_dump() if hasattr(company, 'model_dump') else company
        
        # Create Company node
        company_query = """
        MERGE (c:Company {urn: $urn})
        ON CREATE SET
            c.name = $name,
            c.description = $description,
            c.url = $url,
            c.staffCount = $staffCount,
            c.staffCountRange = $staffCountRange,
            c.createdAt = datetime()
        ON MATCH SET
            c.name = $name,
            c.description = $description,
            c.url = $url,
            c.staffCount = $staffCount,
            c.staffCountRange = $staffCountRange,
            c.updatedAt = datetime()
        RETURN c
        """
        
        staff_count_range = None
        if "staff_count_range" in company_data and company_data["staff_count_range"]:
            staff_count_range = json.dumps(company_data["staff_count_range"])
        
        self._run_query(company_query, {
            "urn": company_data.get("entity_urn") or company_data.get("entityUrn") or company_data.get("urn"),
            "name": company_data.get("name"),
            "description": company_data.get("description", ""),
            "url": company_data.get("url", ""),
            "staffCount": company_data.get("staff_count") or company_data.get("staffCount") or 0,
            "staffCountRange": staff_count_range
        })
        
        # Add industry relationships
        if "company_industries" in company_data and company_data["company_industries"]:
            for industry in company_data["company_industries"]:
                industry_query = """
                MATCH (c:Company {urn: $companyUrn})
                MERGE (i:Industry {name: $industryName.localized_name})
                MERGE (c)-[r:IN_INDUSTRY]->(i)
                RETURN i
                """
                
                self._run_query(industry_query, {
                    "companyUrn": company_data.get("entity_urn") or company_data.get("entityUrn") or company_data.get("urn"),
                    "industryName": industry.get("localizedName") or industry
                })
    
    def store_experience(self, profile_urn: str, experience: Dict[str, Any]):
        """
        Store work experience and create company relationships.
        
        Args:
            profile_urn: Profile URN
            experience: Experience dictionary
        """
        # Extract and store company data first
        company_data = experience["company"]
        company_urn = company_data.get("urn") or company_data.get("companyUrn") or f"urn:li:company:{company_data['name'].replace(' ', '').lower()}"
        
        # Store company if needed
        company_query = """
        MERGE (c:Company {urn: $companyUrn})
        ON CREATE SET
            c.name = $companyName,
            c.createdAt = datetime()
        RETURN c
        """
        
        self._run_query(company_query, {
            "companyUrn": company_urn,
            "companyName": company_data.get("name") or company_data.get("companyName")
        })
        
        # Extract date information
        time_period = experience["time_period"]
        start_date = time_period.get("start_date", {}) or {}
        end_date = time_period.get("end_date", {}) or {}
        is_current = not end_date or not (end_date.get("year") and end_date.get("month"))
        
        # Create unique ID for experience node
        exp_urn = experience.get("entity_urn") or experience.get("entityUrn") or f"exp-{profile_urn}-{company_urn}-{start_date.get('year')}-{start_date.get('month')}"
        
        # Store experience with relationships to profile and company
        exp_query = """
        MATCH (p:Profile {urn: $profileUrn})
        MATCH (c:Company {urn: $companyUrn})
        
        MERGE (e:Experience {urn: $expUrn})
        ON CREATE SET
            e.title = $title,
            e.description = $description,
            e.startYear = $startYear,
            e.startMonth = $startMonth,
            e.endYear = $endYear,
            e.endMonth = $endMonth,
            e.isCurrent = $isCurrent,
            e.locationName = $locationName,
            e.createdAt = datetime()
        ON MATCH SET
            e.title = $title,
            e.description = $description,
            e.startYear = $startYear,
            e.startMonth = $startMonth,
            e.endYear = $endYear,
            e.endMonth = $endMonth,
            e.isCurrent = $isCurrent,
            e.locationName = $locationName,
            e.updatedAt = datetime()
        
        MERGE (p)-[r1:HAS_EXPERIENCE]->(e)
        MERGE (e)-[r2:AT_COMPANY]->(c)
        
        RETURN e, p, c
        """
        
        # Extract location data
        location = experience.get("location", {}) or {}
        location_name = None
        if location:
            location_name = location.get("name") or location.get("locationName")
        
        self._run_query(exp_query, {
            "profileUrn": profile_urn,
            "companyUrn": company_urn,
            "expUrn": exp_urn,
            "title": experience["title"],
            "description": experience.get("description", ""),
            "startYear": start_date.get("year"),
            "startMonth": start_date.get("month"),
            "endYear": end_date.get("year"),
            "endMonth": end_date.get("month"),
            "isCurrent": is_current,
            "locationName": location_name
        })

    def store_transition(self, transition_event: Union[TransitionEvent, dict]):
        """
        Store a job transition event in the Neo4j database.
        
        Args:
            transition_event: Dictionary containing transition data
        """
        transition_query = """
        MATCH (p:Profile {urn: $profileUrn})
        MATCH (oldCompany:Company {urn: $fromCompanyUrn})
        MATCH (newCompany:Company {urn: $toCompanyUrn})
        
        CREATE (t:Transition {
            date: datetime($transitionDate),
            type: $transitionType,
            oldTitle: $oldTitle,
            newTitle: $newTitle,
            locationChange: $locationChange,
            tenureDays: $tenureDays
        })
        
        CREATE (p)-[:HAS_TRANSITION]->(t)
        CREATE (t)-[:FROM_COMPANY]->(oldCompany)
        CREATE (t)-[:TO_COMPANY]->(newCompany)
        
        RETURN t
        """
        transition_event = (transition_event.model_dump()            # if it **is** a model …
            if isinstance(transition_event, TransitionEvent)
            else transition_event)  
          
        # Format transition date
        transition_date = transition_event["transition_date"]
        if isinstance(transition_date, str):
            # If it's already a string, ensure it's in ISO format
            if "T" not in transition_date:
                transition_date = f"{transition_date}T00:00:00"
        else:
            # If it's a datetime object, convert to ISO format string
            transition_date = transition_date.isoformat()
        
        self._run_query(transition_query, {
            "profileUrn": transition_event["profile_urn"],
            "fromCompanyUrn": transition_event["from_company_urn"],
            "toCompanyUrn": transition_event["to_company_urn"],
            "transitionDate": transition_date,
            "transitionType": transition_event["transition_type"],
            "oldTitle": transition_event["old_title"],
            "newTitle": transition_event["new_title"],
            "locationChange": transition_event["location_change"],
            "tenureDays": transition_event["tenure_days"]
        })
    # add batch methods for ease of use
    # def batch_store_profiles(self, profiles: List[LinkedInProfile]):
    #     """
    #     Store multiple LinkedIn profiles in the Neo4j database.
        
    #     Args:
    #         profiles: List of LinkedInProfile model instances
    #     """
    #     for profile in profiles:
    #         self.store_profile(profile)
    
    def batch_store_profiles(self, profiles: List[LinkedInProfile]):
        """
        Complete batch processing solution for storing LinkedIn profiles in Neo4j.
        
        Args:
            profiles: List of LinkedInProfile model instances
        """
        # Process profile nodes first
        profile_dicts = []
        for profile in profiles:
            profile_data = profile.model_dump() if hasattr(profile, 'model_dump') else profile
            profile_dicts.append({
                "urn": profile_data["profile_urn"],
                "profileId": profile_data["profile_id"],
                "firstName": profile_data["first_name"],
                "lastName": profile_data["last_name"],
                "headline": profile_data.get("headline"),
                "summary": profile_data.get("summary"),
                "locationName": profile_data.get("location_name"),
                "industryName": profile_data.get("industry_name"),
                "publicId": profile_data.get("public_id")
            })
        
        # Create all Profile nodes in a single batch operation
        if profile_dicts:
            create_profiles_query = """
            UNWIND $profiles AS profile
            MERGE (p:Profile {urn: profile.urn})
            ON CREATE SET 
                p.profileId = profile.profileId,
                p.firstName = profile.firstName,
                p.lastName = profile.lastName,
                p.headline = profile.headline,
                p.summary = profile.summary,
                p.locationName = profile.locationName,
                p.industryName = profile.industryName,
                p.publicId = profile.publicId,
                p.createdAt = datetime()
            ON MATCH SET
                p.firstName = profile.firstName,
                p.lastName = profile.lastName,
                p.headline = profile.headline,
                p.summary = profile.summary,
                p.locationName = profile.locationName,
                p.industryName = profile.industryName,
                p.updatedAt = datetime()
            """
            self._run_query(create_profiles_query, {"profiles": profile_dicts})
        
        # Process skills
        all_skills = []
        # Process education
        all_education = []
        # Process experience and companies
        all_companies = []
        all_experiences = []
        
        for profile in profiles:
            profile_data = profile.model_dump() if hasattr(profile, 'model_dump') else profile
            profile_urn = profile_data["profile_urn"]
            
            # Collect skills
            if "skills" in profile_data and profile_data["skills"]:
                for skill in profile_data["skills"]:
                    all_skills.append({
                        "profileUrn": profile_urn,
                        "skillName": skill["name"]
                    })
            
            # Collect education
            if "education" in profile_data and profile_data["education"]:
                for edu in profile_data["education"]:
                    school = edu["school"]
                    school_urn = school.get("urn") or f"urn:li:school:{school['name'].replace(' ', '').lower()}"
                    
                    time_period = edu["time_period"]
                    start_date = time_period.get("start_date", {}) or {}
                    end_date = time_period.get("end_date", {}) or {}
                    
                    all_education.append({
                        "profileUrn": profile_urn,
                        "schoolUrn": school_urn,
                        "schoolName": school["name"],
                        "active": school.get("active", True),
                        "degreeName": edu.get("degree_name"),
                        "fieldOfStudy": edu.get("field_of_study"),
                        "startYear": start_date.get("year"),
                        "startMonth": start_date.get("month"),
                        "endYear": end_date.get("year"),
                        "endMonth": end_date.get("month")
                    })
            
            # Collect experience and companies
            if "experience" in profile_data and profile_data["experience"]:
                for exp in profile_data["experience"]:
                    company_data = exp["company"]
                    company_urn = company_data.get("urn") or company_data.get("companyUrn") or f"urn:li:company:{company_data['name'].replace(' ', '').lower()}"
                    
                    # Add company
                    all_companies.append({
                        "urn": company_urn,
                        "name": company_data.get("name") or company_data.get("companyName")
                    })
                    
                    # Add experience
                    time_period = exp["time_period"]
                    start_date = time_period.get("start_date", {}) or {}
                    end_date = time_period.get("end_date", {}) or {}
                    is_current = not end_date or not (end_date.get("year") and end_date.get("month"))
                    
                    location = exp.get("location", {}) or {}
                    location_name = None
                    if location:
                        location_name = location.get("name") or location.get("locationName")
                    
                    exp_urn = exp.get("entity_urn") or exp.get("entityUrn") or f"exp-{profile_urn}-{company_urn}-{start_date.get('year')}-{start_date.get('month')}"
                    
                    all_experiences.append({
                        "profileUrn": profile_urn,
                        "companyUrn": company_urn,
                        "expUrn": exp_urn,
                        "title": exp["title"],
                        "description": exp.get("description", ""),
                        "startYear": start_date.get("year"),
                        "startMonth": start_date.get("month"),
                        "endYear": end_date.get("year"),
                        "endMonth": end_date.get("month"),
                        "isCurrent": is_current,
                        "locationName": location_name
                    })
        
        # Execute batch operations
        
        # 1. Skills
        if all_skills:
            skills_query = """
            UNWIND $skills AS skill
            MATCH (p:Profile {urn: skill.profileUrn})
            MERGE (s:Skill {name: skill.skillName})
            MERGE (p)-[r:HAS_SKILL]->(s)
            """
            self._run_query(skills_query, {"skills": all_skills})
        
        # 2. Schools and education
        if all_education:
            education_query = """
            UNWIND $education AS edu
            
            MERGE (s:School {urn: edu.schoolUrn})
            ON CREATE SET
                s.name = edu.schoolName,
                s.active = edu.active
            
            MATCH (p:Profile {urn: edu.profileUrn})
            MERGE (p)-[r:ATTENDED]->(s)
            ON CREATE SET
                r.degreeName = edu.degreeName,
                r.fieldOfStudy = edu.fieldOfStudy,
                r.startYear = edu.startYear,
                r.startMonth = edu.startMonth,
                r.endYear = edu.endYear,
                r.endMonth = edu.endMonth
            """
            self._run_query(education_query, {"education": all_education})
        
        # 3. Companies
        if all_companies:
            companies_query = """
            UNWIND $companies AS company
            MERGE (c:Company {urn: company.urn})
            ON CREATE SET
                c.name = company.name,
                c.createdAt = datetime()
            ON MATCH SET
                c.name = company.name,
                c.updatedAt = datetime()
            """
            self._run_query(companies_query, {"companies": all_companies})
        
        # 4. Experience
        if all_experiences:
            experience_query = """
            UNWIND $experiences AS exp
            
            MATCH (p:Profile {urn: exp.profileUrn})
            MATCH (c:Company {urn: exp.companyUrn})
            
            MERGE (e:Experience {urn: exp.expUrn})
            ON CREATE SET
                e.title = exp.title,
                e.description = exp.description,
                e.startYear = exp.startYear,
                e.startMonth = exp.startMonth,
                e.endYear = exp.endYear,
                e.endMonth = exp.endMonth,
                e.isCurrent = exp.isCurrent,
                e.locationName = exp.locationName,
                e.createdAt = datetime()
            ON MATCH SET
                e.title = exp.title,
                e.description = exp.description,
                e.startYear = exp.startYear,
                e.startMonth = exp.startMonth,
                e.endYear = exp.endYear,
                e.endMonth = exp.endMonth,
                e.isCurrent = exp.isCurrent,
                e.locationName = exp.locationName,
                e.updatedAt = datetime()
            
            MERGE (p)-[r1:HAS_EXPERIENCE]->(e)
            MERGE (e)-[r2:AT_COMPANY]->(c)
            """
            self._run_query(experience_query, {"experiences": all_experiences})

        print(f"Successfully batched {len(profiles)} profiles with their relationships")
    
    def batch_store_companies(self, companies: List[LinkedInCompany]):
        """
        Store multiple LinkedIn companies in Neo4j efficiently using batch operations.
        
        Args:
            companies: List of LinkedInCompany model instances
        """
        # Convert all companies to dictionaries with normalized property names
        company_dicts = []
        industry_relationships = []
        
        for company in companies:
            company_data = company.model_dump() if hasattr(company, 'model_dump') else company
            
            # Extract primary company data
            company_urn = company_data.get("entity_urn") or company_data.get("entityUrn") or company_data.get("urn")
            
            # Skip if no valid URN
            if not company_urn:
                continue
                
            # Prepare company data
            company_dict = {
                "urn": company_urn,
                "name": company_data.get("name"),
                "description": company_data.get("description", ""),
                "url": company_data.get("url", ""),
                "staffCount": company_data.get("staff_count") or company_data.get("staffCount") or 0,
                "staffCountRange": json.dumps(company_data.get("staff_count_range") or company_data.get("staffCountRange") or {}) if company_data.get("staff_count_range") or company_data.get("staffCountRange") else None
            }
            
            company_dicts.append(company_dict)
            
            # Extract industry relationships
            industries = []
            if "company_industries" in company_data and company_data["company_industries"]:
                for industry in company_data["company_industries"]:
                    industry_name = None
                    if isinstance(industry, dict) and "localized_name" in industry:
                        industry_name = industry["localized_name"]
                    elif isinstance(industry, str):
                        industry_name = industry
                    
                    if industry_name:
                        industry_relationships.append({
                            "companyUrn": company_urn,
                            "industryName": industry_name
                        })
        
        # Execute batch operations
        
        # 1. Create all Company nodes
        if company_dicts:
            companies_query = """
            UNWIND $companies AS company
            MERGE (c:Company {urn: company.urn})
            ON CREATE SET
                c.name = company.name,
                c.description = company.description,
                c.url = company.url,
                c.staffCount = company.staffCount,
                c.staffCountRange = company.staffCountRange,
                c.createdAt = datetime()
            ON MATCH SET
                c.name = company.name,
                c.description = company.description,
                c.url = company.url,
                c.staffCount = company.staffCount,
                c.staffCountRange = company.staffCountRange,
                c.updatedAt = datetime()
            """
            self._run_query(companies_query, {"companies": company_dicts})
            
        # 2. Create Industry nodes and relationships
        if industry_relationships:
            industries_query = """
            UNWIND $industries AS industry
            MATCH (c:Company {urn: industry.companyUrn})
            MERGE (i:Industry {name: industry.industryName})
            MERGE (c)-[r:IN_INDUSTRY]->(i)
            """
            self._run_query(industries_query, {"industries": industry_relationships})
            
        print(f"Successfully stored {len(company_dicts)} companies with their industries")
    
    def batch_store_transitions(self, transitions: List[Union[TransitionEvent,Dict]]):
        """
        Store multiple job transition events in Neo4j efficiently using batch operations.
        
        Args:
            transitions: List of transition event dictionaries
        """
        # Normalize transition data
        transition_dicts = []
        
        for transition in transitions:
            data = (transition.model_dump(by_alias=True)
                    if isinstance(transition, TransitionEvent)
                    else transition)

            # –– normalise the date once –––––––––––––––––––––––
            td = data["transition_date"]
            if isinstance(td, str):
                td = td if "T" in td else f"{td}T00:00:00"
            else:
                td = td.isoformat()

            # –– build the dict that Neo4j will consume ––––––––
            transition_dict = {
                "profileUrn":     data["profile_urn"],
                "fromCompanyUrn": data["from_company_urn"],
                "toCompanyUrn":   data["to_company_urn"],
                "transitionDate": td,
                "transitionType": data["transition_type"],
                "oldTitle":       data["old_title"],
                "newTitle":       data["new_title"],
                "locationChange": data.get("location_change", False),
                "tenureDays":     data.get("tenure_days", 0),
            }
            
            # Only add if we have the minimum required data
            if (transition_dict["profileUrn"] and 
                transition_dict["fromCompanyUrn"] and 
                transition_dict["toCompanyUrn"] and
                transition_dict["transitionDate"]):
                transition_dicts.append(transition_dict)
        
        # Execute batch operation for transitions
        if transition_dicts:
            transitions_query = """
            UNWIND $transitions AS t
            
            MATCH (p:Profile {urn: t.profileUrn})
            MATCH (oldCompany:Company {urn: t.fromCompanyUrn})
            MATCH (newCompany:Company {urn: t.toCompanyUrn})
            
            CREATE (transition:Transition {
                date: datetime(t.transitionDate),
                type: t.transitionType,
                oldTitle: t.oldTitle,
                newTitle: t.newTitle,
                locationChange: t.locationChange,
                tenureDays: t.tenureDays
            })
            
            CREATE (p)-[:HAS_TRANSITION]->(transition)
            CREATE (transition)-[:FROM_COMPANY]->(oldCompany)
            CREATE (transition)-[:TO_COMPANY]->(newCompany)
            """
            self._run_query(transitions_query, {"transitions": transition_dicts})
            
        print(f"Successfully stored {len(transition_dicts)} transition events")

    def batch_store_chunked(self, func, data: List, batch_size=500):
        """Store profiles,companies,or transitions in smaller batches for better performance"""
        total = len(data)
        for i in range(0, total, batch_size):
            chunk = data[i:i+batch_size]
            # Process this smaller chunk using your existing batch method
            func(chunk)
            print(f"Processed {float(min(i+batch_size, total))/float(total)}% of data")

    def find_profile_by_urn(self, profile_urn: str) -> Dict[str, Any]:
        """
        Find a profile by its URN.
        
        Args:
            profile_urn: Profile URN
            
        Returns:
            Profile data as a dictionary
        """
        query = """
        MATCH (p:Profile {urn: $urn})
        RETURN p {
            .*,
            skills: [(p)-[:HAS_SKILL]->(s) | s.name],
            education: [(p)-[edu:ATTENDED]->(school) | {
                school: school.name,
                schoolUrn: school.urn,
                degreeName: edu.degreeName,
                fieldOfStudy: edu.fieldOfStudy,
                startYear: edu.startYear,
                startMonth: edu.startMonth,
                endYear: edu.endYear,
                endMonth: edu.endMonth
            }],
            experience: [(p)-[:HAS_EXPERIENCE]->(e)-[r:AT_COMPANY]->(c) | {
                title: e.title,
                company: c.name,
                companyUrn: c.urn,
                description: e.description,
                startYear: e.startYear,
                startMonth: e.startMonth,
                endYear: e.endYear,
                endMonth: e.endMonth,
                isCurrent: e.isCurrent,
                locationName: e.locationName
            }]
        } as profile
        """
        
        results = self._run_query(query, {"urn": profile_urn})
        return results[0]["profile"] if results else None
    
    def find_company_by_urn(self, company_urn: str) -> Dict[str, Any]:
        """
        Find a company by its URN.
        
        Args:
            company_urn: Company URN
            
        Returns:
            Company data as a dictionary
        """
        query = """
        MATCH (c:Company {urn: $urn})
        RETURN c {
            .*,
            industries: [(c)-[:IN_INDUSTRY]->(i) | i.name]
        } as company
        """
        
        results = self._run_query(query, {"urn": company_urn})
        return results[0]["company"] if results else None
    
    def find_transitions_by_profile(self, profile_urn: str) -> List[Dict[str, Any]]:
        """
        Find all transitions for a profile.
        
        Args:
            profile_urn: Profile URN
            
        Returns:
            List of transition events
        """
        query = """
        MATCH (p:Profile {urn: $urn})-[:HAS_TRANSITION]->(t)-[:FROM_COMPANY]->(fc),
              (t)-[:TO_COMPANY]->(tc)
        RETURN t {
            .*,
            profile: p.urn,
            fromCompany: fc.name,
            fromCompanyUrn: fc.urn,
            toCompany: tc.name,
            toCompanyUrn: tc.urn
        } as transition
        ORDER BY t.date DESC
        """
        
        results = self._run_query(query, {"urn": profile_urn})
        return [r["transition"] for r in results]
    
    def search_profiles(self, 
                      first_name: Optional[str] = None, 
                      last_name: Optional[str] = None,
                      company_name: Optional[str] = None,
                      title: Optional[str] = None,
                      skill: Optional[str] = None,
                      limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for profiles based on various criteria.
        
        Args:
            first_name: First name to search for
            last_name: Last name to search for
            company_name: Company name to search for
            title: Job title to search for
            skill: Skill to search for
            limit: Maximum number of results to return
            
        Returns:
            List of matching profiles
        """
        conditions = []
        params = {}
        
        # Build dynamic query based on provided parameters
        if first_name:
            conditions.append("p.firstName =~ $firstName")
            params["firstName"] = f"(?i).*{first_name}.*"
        
        if last_name:
            conditions.append("p.lastName =~ $lastName")
            params["lastName"] = f"(?i).*{last_name}.*"
        
        if company_name:
            conditions.append("EXISTS { MATCH (p)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c) WHERE c.name =~ $companyName }")
            params["companyName"] = f"(?i).*{company_name}.*"
        
        if title:
            conditions.append("EXISTS { MATCH (p)-[:HAS_EXPERIENCE]->(e) WHERE e.title =~ $title }")
            params["title"] = f"(?i).*{title}.*"
        
        if skill:
            conditions.append("EXISTS { MATCH (p)-[:HAS_SKILL]->(s) WHERE s.name =~ $skill }")
            params["skill"] = f"(?i).*{skill}.*"
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        params["limit"] = limit
        
        query = f"""
        MATCH (p:Profile)
        WHERE {where_clause}
        RETURN p {{
            .*,
            skills: [(p)-[:HAS_SKILL]->(s) | s.name],
            currentExperience: head([
                (p)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c) 
                WHERE e.isCurrent = true OR e.endYear IS NULL
                | {{ title: e.title, company: c.name }}
            ])
        }} as profile
        LIMIT $limit
        """
        
        results = self._run_query(query, params)
        return [r["profile"] for r in results]
    
    def get_company_transition_stats(self, company_urn: str) -> Dict[str, Any]:
        """
        Get transition statistics for a company.
        
        Args:
            company_urn: Company URN
            
        Returns:
            Dictionary with transition statistics
        """
        query = """
        MATCH (c:Company {urn: $companyUrn})
        
        // Incoming transitions (people joining)
        OPTIONAL MATCH (p1:Profile)-[:HAS_TRANSITION]->(t1:Transition)-[:TO_COMPANY]->(c)
        WITH c, count(t1) as incomingCount, collect(t1) as incomingTransitions
        
        // Outgoing transitions (people leaving)
        OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t2:Transition)-[:FROM_COMPANY]->(c)
        
        // Top companies people come from
        OPTIONAL MATCH (t1in:Transition)-[:TO_COMPANY]->(c),
                      (t1in)-[:FROM_COMPANY]->(fromCompany)
        WITH c, incomingCount, incomingTransitions, count(t2) as outgoingCount,
             fromCompany, count(t1in) as fromCount
        
        // Top companies people go to
        OPTIONAL MATCH (t2out:Transition)-[:FROM_COMPANY]->(c),
                      (t2out)-[:TO_COMPANY]->(toCompany)
        WITH c, incomingCount, outgoingCount, 
             fromCompany, fromCount, toCompany, count(t2out) as toCount
        
        // Aggregate top companies
        WITH c, incomingCount, outgoingCount,
             collect({company: fromCompany.name, count: fromCount}) as topSourceCompanies,
             collect({company: toCompany.name, count: toCount}) as topDestinationCompanies
        
        RETURN {
            companyName: c.name,
            incomingTransitions: incomingCount,
            outgoingTransitions: outgoingCount,
            topSourceCompanies: [x in topSourceCompanies WHERE x.company IS NOT NULL | x],
            topDestinationCompanies: [x in topDestinationCompanies WHERE x.company IS NOT NULL | x]
        } as stats
        """
        
        results = self._run_query(query, {"companyUrn": company_urn})
        return results[0]["stats"] if results else {}
    
    # def get_skill_trends(self, limit: int = 10) -> List[Dict[str, Any]]:
    #     """
    #     Get trending skills based on recent transitions.
        
    #     Args:
    #         limit: Maximum number of trending skills to return
            
    #     Returns:
    #         List of trending skills with counts
    #     """
    #     query = """
    #     MATCH (p:Profile)-[:HAS_SKILL]->(s:Skill)
    #     WITH s, count(p) as profileCount
        
    #     // Find transitions from profiles with this skill in the last year
    #     OPTIONAL MATCH (p2:Profile)-[:HAS_SKILL]->(s)
    #                   -[:HAS_TRANSITION]->(t:Transition)
    #     WHERE datetime(t.date) >= datetime.truncate('year', datetime()) - duration('P1Y')
        
    #     WITH s, profileCount, count(t) as transitionCount
        
    #     // Calculate a trend score (higher is more trending)
    #     WITH s, profileCount, transitionCount,
    #          toFloat(transitionCount) / toFloat(profileCount + 1) as trendScore
        
    #     RETURN {
    #         skillName: s.name,
    #         profileCount: profileCount,
    #         recentTransitions: transitionCount,
    #         trendScore: trendScore
    #     } as skill
    #     ORDER BY skill.trendScore DESC, skill.profileCount DESC
    #     LIMIT $limit
    #     """
        
    #     results = self._run_query(query, {"limit": limit})
    #     return [r["skill"] for r in results]
    
    # def recommend_connections(self, profile_urn: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recommend potential connections for a profile based on common companies, schools, etc.
        
        Args:
            profile_urn: Profile URN to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended profiles with connection strength
        """
        query = """
        MATCH (p:Profile {urn: $profileUrn})
        
        // Find other profiles that share companies
        OPTIONAL MATCH (p)-[:HAS_EXPERIENCE]->(e1)-[:AT_COMPANY]->(c)<-[:AT_COMPANY]-(e2)<-[:HAS_EXPERIENCE]-(other)
        WHERE p <> other
        WITH p, other, count(c) as sharedCompanies
        
        // Find other profiles that share schools
        OPTIONAL MATCH (p)-[:ATTENDED]->(s)<-[:ATTENDED]-(other)
        WHERE p <> other
        WITH p, other, sharedCompanies, count(s) as sharedSchools
        
        // Find other profiles that share skills
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(skill)<-[:HAS_SKILL]-(other)
        WHERE p <> other
        WITH p, other, sharedCompanies, sharedSchools, count(skill) as sharedSkills
        
        // Calculate connection strength score
        WITH p, other, 
             5 * sharedCompanies + 3 * sharedSchools + sharedSkills as connectionStrength
        WHERE connectionStrength > 0
        
        RETURN other {
            .*,
            currentExperience: head([
                (other)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c) 
                WHERE e.isCurrent = true OR e.endYear IS NULL
                | { title: e.title, company: c.name }
            ]),
            connectionStrength: connectionStrength,
            sharedCompanies: [(p)-[:HAS_EXPERIENCE]->()-[:AT_COMPANY]->(c)<-[:AT_COMPANY]-()<-[:HAS_EXPERIENCE]-(other) | c.name],
            sharedSkills: [(p)-[:HAS_SKILL]->(s)<-[:HAS_SKILL]-(other) | s.name]
        } as recommendation
        ORDER BY recommendation.connectionStrength DESC
        LIMIT $limit
        """
        
        results = self._run_query(query, {"profileUrn": profile_urn, "limit": limit})
        return [r["recommendation"] for r in results]
    
    def clear_database(self):
        """WARNING: Clear the entire database. Use with caution!"""
        query = """
        MATCH (n)
        DETACH DELETE n
        """
        self._run_query(query)
        print("Neo4j database cleared")
## _________________________________________________________________________________________________________________________
## Module Wide Methods for Neo4j
## _________________________________________________________________________________________________________________________

def send_to_neo4j(profiles: List[LinkedInProfile], companies: List[LinkedInCompany]):
    """
    Send LinkedIn profiles and companies to Neo4j database.
    Compatible with the existing send_to_druid function interface.
    
    Args:
        profiles: List of LinkedInProfile objects
        companies: List of LinkedInCompany objects
    """
    db = Neo4jDatabase()
    
    try:
        # Set up database constraints if needed
        db.setup_constraints()
        
        # Store companies first to ensure they exist
        print(f"Storing {len(companies)} companies in Neo4j...")
        db.batch_store_chunked(db.batch_store_companies,companies)
        
        # Store profiles and their relationships
        print(f"Storing {len(profiles)} profiles in Neo4j...")
        db.batch_store_chunked(db.batch_store_profiles,profiles)
        
        print("Successfully stored data in Neo4j database")
    finally:
        # Ensure database connection is closed
        db.close()

def send_transition_to_neo4j(transition_event: TransitionEvent) -> bool:
    """
    Send a transition event to Neo4j.
    Compatible with the existing send_transition_update function interface.
    
    Args:
        transition_event: Dictionary containing transition data
        
    Returns:
        True if successful, False otherwise
    """
    db = Neo4jDatabase()
    
    try:
        # Store transition
        db.store_transition(transition_event)
        print(f"Successfully stored transition for profile: {transition_event['profile_urn']}")
        return True
    except Exception as e:
        print(f"Error storing transition in Neo4j: {e}")
        return False
    finally:
        db.close()


def query_neo4j(cypher_query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute a custom Cypher query on the Neo4j database.
    
    Args:
        cypher_query: Cypher query string
        params: Query parameters
        
    Returns:
        Query results as a list of dictionaries
    """
    db = Neo4jDatabase()
    
    try:
        results = db._run_query(cypher_query, params)
        return results
    finally:
        db.close()

## _________________________________________________________________________________________________________________________
## Second Order Analysis Class for Neo4j db
## _________________________________________________________________________________________________________________________

class Neo4jProfileAnalyzer:
    """
    Helper class for analyzing LinkedIn profile data in Neo4j.
    Provides higher-level functions for common analysis tasks.
    """
    
    def __init__(self):
        """Initialize the analyzer with a database connection."""
        self.db = Neo4jDatabase()
    
    def close(self):
        """Close the database connection."""
        self.db.close()
    
    def get_career_path_analysis(self, profile_urn: str) -> Dict[str, Any]:
        """
        Analyze the career path of a profile.
        
        Args:
            profile_urn: Profile URN
            
        Returns:
            Dictionary with career path analysis
        """
        query = """
        MATCH (p:Profile {urn: $profileUrn})-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
                
        WITH p, e, c
        ORDER BY e.startYear, e.startMonth
                
        WITH p, collect({
            title: e.title,
            company: c.name,
            startYear: e.startYear,
            startMonth: e.startMonth,
            endYear: e.endYear,
            endMonth: e.endMonth,
            isCurrent: e.isCurrent,
            duration: CASE
                WHEN e.endYear IS NULL THEN 
                    (datetime().year - e.startYear) * 12 + (datetime().month - e.startMonth)
                ELSE 
                    (e.endYear - e.startYear) * 12 + (e.endMonth - e.startMonth)
            END
        }) as experiences
                
        // Calculate average tenure
        WITH p, experiences,
            reduce(total = 0, exp in [x in experiences WHERE x.duration IS NOT NULL] | total + exp.duration) / 
            size([x in experiences WHERE x.duration IS NOT NULL]) as averageTenureMonths
                
        // Get education
        OPTIONAL MATCH (p)-[edu:ATTENDED]->(s:School)
        WITH p, experiences, averageTenureMonths, 
            collect({school: s.name, degree: edu.degreeName, field: edu.fieldOfStudy}) as education
                
        // Get skills
        MATCH (p)-[:HAS_SKILL]->(skill)
        WITH p, experiences, averageTenureMonths, education, collect(skill.name) as skills
                
        // Final return with all calculations
        RETURN {
            profileName: p.firstName + ' ' + p.lastName,
            headline: p.headline,
            careerPath: experiences,
            education: education,
            skills: skills,
            averageTenureMonths: averageTenureMonths,
            totalExperience: reduce(total = 0, exp in experiences | total + exp.duration),
            numberOfCompanies: size(experiences),
            titleProgression: [exp in experiences | exp.title]
        } as analysis
        """
        
        results = self.db._run_query(query, {"profileUrn": profile_urn})
        return results[0]["analysis"] if results else {}
    
    def get_company_talent_flow(self, company_urn: str, time_period: str = "P1Y") -> Dict[str, Any]:
        """
        Analyze talent flow for a company over a specified time period.
        
        Args:
            company_urn: Company URN
            time_period: Time period for analysis (ISO-8601 format) 
            - "1 YEAR" → "P1Y"
            - "6 MONTHS" → "P6M"
            - "3 MONTHS" → "P3M"
            - "1 MONTH" → "P1M"
            - "1 WEEK" → "P7D"
            
        Returns:
            Dictionary with talent flow analysis
        """
        query = """
        MATCH (c:Company {urn: $companyUrn})
                
        // Calculate time threshold
        WITH c, datetime() - duration($timePeriod) as cutoffDate
                
        // Incoming transitions (people joining)
        OPTIONAL MATCH (p1:Profile)-[:HAS_TRANSITION]->(t1:Transition)-[:TO_COMPANY]->(c)
        WHERE datetime(t1.date) >= cutoffDate
        WITH c, cutoffDate, count(t1) as hiringCount
                
        // Outgoing transitions (people leaving)
        OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t2:Transition)-[:FROM_COMPANY]->(c)
        WHERE datetime(t2.date) >= cutoffDate
        WITH c, cutoffDate, hiringCount, count(t2) as attritionCount
                
        // Calculate net talent flow
        WITH c, hiringCount, attritionCount, hiringCount - attritionCount as netTalentFlow
                
        // Get current employee count (approximation based on experiences)
        MATCH (p3:Profile)-[:HAS_EXPERIENCE]->(e3)-[:AT_COMPANY]->(c)
        WHERE e3.isCurrent = true OR e3.endYear IS NULL

        // Collect employee count before creating final return
        WITH c, hiringCount, attritionCount, netTalentFlow, count(p3) as currentEmployeeCount
                
        RETURN {
            companyName: c.name,
            companyUrn: c.urn,
            hiringCount: hiringCount,
            attritionCount: attritionCount,
            netTalentFlow: netTalentFlow,
            currentEmployeeCount: currentEmployeeCount,
            talentFlowRate: round(100.0 * toFloat(netTalentFlow) / toFloat(currentEmployeeCount + 1), 2),
            timePeriod: $timePeriod
        } as analysis
        """
        
        results = self.db._run_query(query, {"companyUrn": company_urn, "timePeriod": time_period})
        return results[0]["analysis"] if results else {}
    
    def get_skill_cluster_analysis(self) -> List[Dict[str, Any]]:
        """
        Perform skill cluster analysis to identify related skill groups.
        
        Returns:
            List of skill clusters with related skills
        """
        query = """
        // Find pairs of skills that frequently appear together
        MATCH (s1:Skill)<-[:HAS_SKILL]-(p:Profile)-[:HAS_SKILL]->(s2:Skill)
        WHERE s1 <> s2
        WITH s1, s2, count(p) as coOccurrence
        WHERE coOccurrence > 5  // Minimum co-occurrence threshold

        // Calculate similarity score (Jaccard similarity)
        MATCH (pa:Profile)-[:HAS_SKILL]->(s1)
        WITH s1, s2, coOccurrence, count(pa) as s1Count

        MATCH (pb:Profile)-[:HAS_SKILL]->(s2)
        WITH s1, s2, coOccurrence, s1Count, count(pb) as s2Count

        WITH s1, s2, coOccurrence, s1Count, s2Count,
            1.0 * coOccurrence / (s1Count + s2Count - coOccurrence) as similarity
        WHERE similarity > 0.1  // Minimum similarity threshold

        // Group skills into clusters using connected components
        WITH collect({skill1: s1.name, skill2: s2.name, similarity: similarity}) as skillPairs

        CALL {
            WITH skillPairs
            UNWIND skillPairs as pair
            
            MERGE (sa:SkillNode {name: pair.skill1})
            MERGE (sb:SkillNode {name: pair.skill2})
            MERGE (sa)-[r:RELATED {similarity: pair.similarity}]->(sb)
            
            WITH collect(distinct sa.name) + collect(distinct sb.name) as allSkillNames
            
            CALL {
                WITH allSkillNames
                UNWIND allSkillNames as name
                MERGE (s:SkillNode {name: name})
                RETURN count(s) as nodeCount
            }
            
            CALL gds.graph.project(
                'skillGraph',
                'SkillNode',
                'RELATED',
                {
                    relationshipProperties: 'similarity'
                }
            )
            
            CALL gds.louvain.stream('skillGraph')
            YIELD nodeId as louvainNodeId, communityId
            
            WITH louvainNodeId, communityId
            
            MATCH (s:SkillNode)
            WHERE id(s) = louvainNodeId
            
            RETURN s.name as skillName, communityId as clusterId
        }

        // Clean up temporary graph and nodes
        CALL gds.graph.drop('skillGraph')
        MATCH (s:SkillNode)
        DETACH DELETE s

        // Group skills by cluster
        WITH skillName, clusterId
        ORDER BY clusterId, skillName

        WITH clusterId, collect(skillName) as skills
        WHERE size(skills) > 2  // Only include clusters with at least 3 skills

        // Identify most common skills for cluster naming
        MATCH (s:Skill)
        WHERE s.name IN skills
        OPTIONAL MATCH (p:Profile)-[:HAS_SKILL]->(s)
        WITH clusterId, skills, s, count(p) as popularity
        ORDER BY clusterId, popularity DESC

        WITH clusterId, skills, collect(s.name)[0] as primarySkill

        RETURN {
            clusterId: clusterId,
            clusterName: primarySkill + ' Cluster',
            skills: skills,
            primarySkill: primarySkill,
            skillCount: size(skills)
        } as cluster
        ORDER BY cluster.skillCount DESC
        """
        
        # Note: This query uses GDS (Graph Data Science) library which needs to be installed
        # If GDS is not available, a simpler clustering can be implemented
        
        try:
            results = self.db._run_query(query)
            return [r["cluster"] for r in results]
        except Exception as e:
            print(f"Error in skill cluster analysis: {e}")
            
            # Fallback to simpler clustering if GDS is not available
            fallback_query = """
            MATCH (s1:Skill)<-[:HAS_SKILL]-(p:Profile)-[:HAS_SKILL]->(s2:Skill)
            WHERE s1 <> s2
            WITH s1, s2, count(p) as coOccurrence
            WHERE coOccurrence > 5
            
            WITH s1.name as skill1, s2.name as skill2, coOccurrence
            ORDER BY coOccurrence DESC
            LIMIT 100
            
            WITH collect({skill1: skill1, skill2: skill2, count: coOccurrence}) as pairs
            
            // Manual clustering based on top co-occurrences
            UNWIND pairs as pair
            WITH pair.skill1 as skill, collect(pair.skill2) as relatedSkills
            
            RETURN {
                clusterId: apoc.util.md5([skill] + relatedSkills),
                clusterName: skill + ' Group',
                skills: [skill] + relatedSkills,
                primarySkill: skill,
                skillCount: 1 + size(relatedSkills)
            } as cluster
            ORDER BY cluster.skillCount DESC
            LIMIT 10
            """
            
            try:
                results = self.db._run_query(fallback_query)
                return [r["cluster"] for r in results]
            except Exception as fallback_error:
                print(f"Error in fallback skill analysis: {fallback_error}")
                return []

## _________________________________________________________________________________________________________________________
## Mock Data Integration Functions
## _________________________________________________________________________________________________________________________


def generate_and_store_mock_data(num_profiles: int = 100):
    """
    Generate mock data and store it in Neo4j.
    
    Args:
        num_profiles: Number of profiles to generate
    """
    from mock_enhanced import generate_mock_data_for_testing
    
    print(f"Generating {num_profiles} mock profiles...")
    dataset = generate_mock_data_for_testing(num_profiles=num_profiles)
    
    # Convert to Pydantic models
    profiles = []
    for profile_data in dataset["profiles"]:
        try:
            profile = LinkedInProfile(**profile_data)
            profiles.append(profile)
        except Exception as e:
            print(f"Error converting profile: {e}")
    
    companies = []
    for company_data in dataset["companies"]:
        try:
            company = LinkedInCompany(**company_data)
            companies.append(company)
        except Exception as e:
            print(f"Error converting company: {e}")
    
    # Store in Neo4j
    send_to_neo4j(profiles=profiles, companies=companies)
    
    # Store transitions
    db = Neo4jDatabase()
    try:
        print(f"Storing {len(dataset['transitions'])} transitions in Neo4j...")
        db.batch_store_chunked(db.batch_store_transitions,dataset["transitions"])
    finally:
        db.close()
    
    print("Mock data generation and storage complete")
    return len(profiles), len(companies), len(dataset["transitions"])
