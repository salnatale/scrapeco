import os
import json
import random
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import copy
import itertools
from pydantic import ValidationError

from models import (
    LinkedInProfile, LinkedInCompany, Experience, 
    Company, TimePeriod, Location, School, Education, Skill, TransitionEvent
)
from openai import OpenAI

# Constants
# Constants for realistic data generation
JOB_TITLES = [
    "Software Engineer", "Senior Software Engineer", "Staff Software Engineer", "Principal Engineer",
    "Engineering Manager", "Director of Engineering", "VP of Engineering", "CTO",
    "Product Manager", "Senior Product Manager", "Director of Product", "VP of Product",
    "Data Scientist", "Senior Data Scientist", "Lead Data Scientist", "Data Science Manager",
    "UI/UX Designer", "Product Designer", "Design Lead", "Creative Director",
    "Marketing Specialist", "Marketing Manager", "Growth Marketer", "CMO",
    "Sales Representative", "Account Executive", "Sales Manager", "VP of Sales",
    "Customer Success Manager", "Technical Support Engineer", "DevOps Engineer", "SRE"
]
TITLES_CAREER_STAGES = {
    "early": ["Software Engineer", "Data Scientist", "UI/UX Designer",  "Product Manager", "Marketing Specialist", "Sales Representative", "Customer Success Manager"],
    "mid": ["Senior Software Engineer", "Staff Software Engineer", "Engineering Manager", "Senior Product Manager", "Senior Data Scientist", "Lead Data Scientist", "Data Science Manager", "Product Designer", "Marketing Manager", "Account Executive", "Sales Manager", "Technical Support Engineer"],
    "senior": ["Principal Engineer", "Director of Engineering", " Engineering Manager", "Director of Product", "Lead Data Scientist", "Data Science Manager", "Design Lead", "Creative Director", "SRE"],
    "executive": [ "VP of Engineering", "CTO", "VP of Product", "CMO", "VP of Sales"]
}

DEGREE_FIELDS = ["Computer Science", "Data Science", 
                 "Electrical Engineering", "Information Technology"]

ALLOWED_TRANSITIONS = {
    # from education
    "Computer Science": ["Software Engineer", "Data Scientist", "UI/UX Designer"],
    "Data Science": ["Data Scientist", "Software Engineer"],
    "Electrical Engineering": ["Software Engineer", "Data Scientist"],
    "Information Technology": [ "Data Scientist","Marketing Specialist", "Sales Representative", "Customer Success Manager"],

    # Engineering track
    "Software Engineer": ["Software Engineer","Senior Software Engineer", "Engineering Manager","Data Scientist"],
    "Senior Software Engineer": ["Senior Software Engineer","Staff Software Engineer", "Engineering Manager"],
    "Staff Software Engineer": ["Principal Engineer", "Engineering Manager", "Staff Software Engineer"],
    "Principal Engineer": ["Engineering Manager","Director of Engineering", "Principal Engineer"],
    "Engineering Manager": ["Director of Engineering", "Engineering Manager"],
    "Director of Engineering": ["VP of Engineering", "Director of Engineering"],
    "VP of Engineering": ["CTO", "VP of Engineering"],
    "CTO": ["CTO"],
    
    # Product track
    "Product Manager": ["Senior Product Manager", "Product Manager"],
    "Senior Product Manager": ["Director of Product", "Senior Product Manager"],
    "Director of Product": ["VP of Product", "Director of Product"],
    "VP of Product": ["CTO", "VP of Product"],
    
    # Data Science track
    "Data Scientist": ["Senior Data Scientist", "Lead Data Scientist", "Data Science Manager", "Software Engineer", "Product Manager", "Data Scientist"],
    "Senior Data Scientist": ["Lead Data Scientist", "Data Science Manager", "Senior Data Scientist"],
    "Lead Data Scientist": ["Data Science Manager", "Lead Data Scientist"],
    "Data Science Manager": ["Director of Engineering", "Data Science Manager"],
    
    # Design track
    "UI/UX Designer": ["Product Designer", "UI/UX Designer", "Design Lead"],
    "Product Designer": ["Design Lead", "Creative Director"],
    "Design Lead": ["Creative Director", "Design Lead"],
    "Creative Director": ["Creative Director"],
    
    # Marketing track
    "Marketing Specialist": ["Marketing Manager", "Growth Marketer", "Marketing Specialist"],
    "Marketing Manager": ["Growth Marketer", "CMO"],
    "Growth Marketer": ["CMO"],
    "CMO": ["CMO"],
    
    # Sales track
    "Sales Representative": ["Account Executive", "Sales Representative"],
    "Account Executive": ["Sales Manager"],
    "Sales Manager": ["VP of Sales"],
    "VP of Sales": ["CTO"],
    
    # Other technical roles
    "Customer Success Manager": ["Technical Support Engineer","Customer Success Manager"],
    "Technical Support Engineer": ["DevOps Engineer"],
    "DevOps Engineer": ["SRE"],
    "SRE": ["Principal Engineer"], 

}

TECH_COMPANIES = [
    {"name": "Google", "size": "large", "industry": "Technology"},
    {"name": "Microsoft", "size": "large", "industry": "Technology"},
    {"name": "Amazon", "size": "large", "industry": "E-commerce/Technology"},
    {"name": "Apple", "size": "large", "industry": "Technology"},
    {"name": "Meta", "size": "large", "industry": "Social Media/Technology"},
    {"name": "Netflix", "size": "large", "industry": "Entertainment/Technology"},
    {"name": "Spotify", "size": "medium", "industry": "Music/Technology"},
    {"name": "Airbnb", "size": "medium", "industry": "Travel/Technology"},
    {"name": "Uber", "size": "large", "industry": "Transportation/Technology"},
    {"name": "Lyft", "size": "medium", "industry": "Transportation/Technology"},
    {"name": "Twitter", "size": "medium", "industry": "Social Media/Technology"},
    {"name": "LinkedIn", "size": "large", "industry": "Social Media/Technology"},
    {"name": "Salesforce", "size": "large", "industry": "CRM/Technology"},
    {"name": "Adobe", "size": "large", "industry": "Software/Technology"},
    {"name": "Stripe", "size": "medium", "industry": "Fintech/Technology"},
    {"name": "Slack", "size": "medium", "industry": "Communication/Technology"},
    {"name": "Dropbox", "size": "medium", "industry": "Cloud Storage/Technology"},
    {"name": "Shopify", "size": "medium", "industry": "E-commerce/Technology"},
    {"name": "Twilio", "size": "medium", "industry": "Communication/Technology"},
    {"name": "Zoom", "size": "medium", "industry": "Communication/Technology"}
]

STARTUP_COMPANIES = [
    {"name": "TechNova", "size": "small", "industry": "AI/ML"},
    {"name": "QuantumLeap", "size": "small", "industry": "Quantum Computing"},
    {"name": "GreenWave", "size": "small", "industry": "Clean Energy"},
    {"name": "HealthPulse", "size": "small", "industry": "Health Tech"},
    {"name": "CryptoFusion", "size": "small", "industry": "Blockchain"},
    {"name": "DataSphere", "size": "small", "industry": "Big Data"},
    {"name": "RoboMinds", "size": "small", "industry": "Robotics"},
    {"name": "VirtualVista", "size": "small", "industry": "AR/VR"},
    {"name": "EcoSmart", "size": "small", "industry": "Sustainability Tech"},
    {"name": "FinFlow", "size": "small", "industry": "Fintech"}
]

# Combined company list
COMPANIES = TECH_COMPANIES + STARTUP_COMPANIES

UNIVERSITIES = [
    {"name": "Stanford University", "tier": "top"},
    {"name": "Massachusetts Institute of Technology", "tier": "top"},
    {"name": "Harvard University", "tier": "top"},
    {"name": "University of California, Berkeley", "tier": "top"},
    {"name": "California Institute of Technology", "tier": "top"},
    {"name": "University of Michigan", "tier": "high"},
    {"name": "University of Washington", "tier": "high"},
    {"name": "University of Texas at Austin", "tier": "high"},
    {"name": "Georgia Institute of Technology", "tier": "high"},
    {"name": "University of Illinois Urbana-Champaign", "tier": "high"},
    {"name": "San Jose State University", "tier": "mid"},
    {"name": "Arizona State University", "tier": "mid"},
    {"name": "Portland State University", "tier": "mid"},
    {"name": "University of Oregon", "tier": "mid"},
    {"name": "Colorado State University", "tier": "mid"}
]

LOCATIONS = [
    {"name": "San Francisco, CA", "region": "Bay Area", "country": "United States"},
    {"name": "Seattle, WA", "region": "Pacific Northwest", "country": "United States"},
    {"name": "Austin, TX", "region": "Southwest", "country": "United States"},
    {"name": "New York, NY", "region": "Northeast", "country": "United States"},
    {"name": "Boston, MA", "region": "Northeast", "country": "United States"},
    {"name": "Los Angeles, CA", "region": "Southern California", "country": "United States"},
    {"name": "Chicago, IL", "region": "Midwest", "country": "United States"},
    {"name": "Denver, CO", "region": "Mountain West", "country": "United States"},
    {"name": "Portland, OR", "region": "Pacific Northwest", "country": "United States"},
    {"name": "Atlanta, GA", "region": "Southeast", "country": "United States"},
    {"name": "London", "region": "Greater London", "country": "United Kingdom"},
    {"name": "Berlin", "region": "Berlin", "country": "Germany"},
    {"name": "Singapore", "region": "Singapore", "country": "Singapore"},
    {"name": "Sydney", "region": "New South Wales", "country": "Australia"},
    {"name": "Toronto", "region": "Ontario", "country": "Canada"}
]

TECH_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Rust", "Swift",
    "React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "Spring Boot",
    "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Terraform",
    "TensorFlow", "PyTorch", "Scikit-learn", "SQL", "MongoDB", "Redis", "Kafka",
    "GraphQL", "REST APIs", "Microservices", "CI/CD", "Git", "Agile Methodologies"
]

SOFT_SKILLS = [
    "Leadership", "Communication", "Teamwork", "Problem Solving", 
    "Critical Thinking", "Project Management", "Time Management",
    "Collaboration", "Creativity", "Adaptability", "Mentoring"
]

FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "William", "Sophia", "James",
    "Isabella", "Benjamin", "Mia", "Elijah", "Charlotte", "Lucas", "Amelia",
    "Mason", "Harper", "Ethan", "Evelyn", "Oliver", "Abigail", "Jacob",
    "Emily", "Michael", "Elizabeth", "Daniel", "Sofia", "Matthew", "Avery",
    "Henry", "Ella", "Jackson", "Scarlett", "Samuel", "Grace", "Sebastian",
    "Chloe", "David", "Victoria", "Joseph", "Riley", "Carter", "Aria",
    "Owen", "Lily", "Wyatt", "Aubrey", "John", "Zoey", "Jack", "Hannah"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
    "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
    "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis",
    "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King", "Wright",
    "Lopez", "Hill", "Scott", "Green", "Adams", "Baker", "Gonzalez", "Nelson",
    "Carter", "Mitchell", "Perez", "Roberts", "Turner", "Phillips", "Campbell",
    "Parker", "Evans", "Edwards", "Collins", "Stewart", "Sanchez", "Morris"
]

class LinkedInDataGenerator:
    """A comprehensive system for generating realistic mock LinkedIn data."""
    
    def __init__(self, use_openai: bool = False, openai_api_key: Optional[str] = None):
        """
        Initialize the data generator.
        
        Args:
            use_openai: Whether to use OpenAI for more realistic data generation
            openai_api_key: OpenAI API key if use_openai is True
        """
        self.use_openai = use_openai
        if use_openai:
            self.openai_client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        
        # proper URN's
        self.companies = self._initialize_companies()
        
        self.universities = self._initialize_universities()
        
        self.profiles = []

    def _initialize_companies(self) -> List[Dict[str, Any]]:
        """Create a database of companies with proper URNs."""
        companies = []
        for idx, company_data in enumerate(COMPANIES):
            company_id = 1000000 + idx
            urn = f"urn:li:company:{company_id}"
            
            # Add size ranges based on company size
            employee_range = {
                "small": {"start": 10, "end": 200},
                "medium": {"start": 201, "end": 5000},
                "large": {"start": 5001, "end": 100000}
            }.get(company_data["size"], {"start": 10, "end": 200})
            
            companies.append({
                "name": company_data["name"],
                "urn": urn,
                "id": str(company_id),
                "industry": company_data["industry"],
                "size": company_data["size"],
                "employee_range": employee_range,
                "logo_url": f"https://example.com/logos/{company_data['name'].lower().replace(' ', '_')}.png"
            })
        return companies
    
    def _initialize_universities(self) -> List[Dict[str, Any]]:
        """Create a database of universities with proper URNs."""
        universities = []
        for idx, university_data in enumerate(UNIVERSITIES):
            school_id = 2000000 + idx
            urn = f"urn:li:school:{school_id}"
            
            universities.append({
                "name": university_data["name"],
                "urn": urn,
                "id": str(school_id),
                "tier": university_data["tier"],
                "logo_url": f"https://example.com/logos/{university_data['name'].lower().replace(' ', '_')}.png"
            })
        return universities
    
    def generate_time_period(self, 
                            start_year_range: Tuple[int, int] = (2010, 2022),
                            duration_range: Tuple[int, int] = (6, 36), current = False) -> Dict[str, Any]:
        """
        Generate a realistic time period for experience or education.
        
        Args:
            start_year_range: Range of possible start years (min, max)
            duration_range: Range of possible durations in months (min, max)
            
        Returns:
            A dictionary with startDate and endDate (or None for current positions)
        """
        start_year = random.randint(*start_year_range)
        start_month = random.randint(1, 12)
        
        # Calculate end date
        duration_months = random.randint(*duration_range)
        
        # Add months to start date to get end date
        end_month = ((start_month + duration_months - 1) % 12) + 1
        end_year = start_year + (start_month + duration_months - 1) // 12
        
        # 20% chance of being a current position (no end date)
        is_current = current
        
        time_period = {
            "startDate": {
                "year": start_year,
                "month": start_month
            }
        }
        
        if not is_current:
            time_period["endDate"] = {
                "year": end_year,
                "month": end_month
            }
        
        return time_period
    def generate_location(self) -> Dict[str, Any]:
        """Generate a random location."""
        location_data = random.choice(LOCATIONS)
        return {
            "locationName": location_data["name"],
            "geoLocationName": location_data["region"],
            "geoUrn": f"urn:li:geo:{random.randint(1000, 9999)}",
            "region": location_data["region"]
        }
    
    def generate_company(self, tier: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a company object based on optional tier preferences.
        
        Args:
            tier: Optional preference for company size ('small', 'medium', 'large')
            
        Returns:
            Company data dictionary
        """
        if tier:
            filtered_companies = [c for c in self.companies if c["size"] == tier]

            # fallback on self.companies if no companies of the specified tier
            company_data = random.choice(filtered_companies or self.companies)
        else:
            company_data = random.choice(self.companies)
        
        return {
            "companyName": company_data["name"],
            "companyUrn": company_data["urn"],
            "companyLogoUrl": company_data["logo_url"],
            "employeeCountRange": company_data["employee_range"],
            "industries": [company_data["industry"]]
        }
    
    def generate_experience(self, 
                          career_stage: str = "mid",  # early, mid, senior, executive
                          start_year_range: Optional[Tuple[int, int]] = None, current = False,prev_experience = None,education_field = None) -> Dict[str, Any]:
        """
        Generate a realistic job experience entry.
        
        Args:
            career_stage: Career level to generate appropriate titles and companies
            start_year_range: Optional specific year range for this experience
            
        Returns:
            Experience data dictionary
        """
        if not prev_experience:
            if education_field:
                
                title_pool_1 = ALLOWED_TRANSITIONS[education_field] 
                title_pool_2 = TITLES_CAREER_STAGES[career_stage]
                title_pool = list(set(title_pool_1).intersection(title_pool_2)) or title_pool_1
                # pick title based on stage from title pool
                title = random.choice(title_pool)
                company_tier = random.choice(["small", "medium", "large"])
            else:
                title_pool = TITLES_CAREER_STAGES[career_stage]
                title = random.choice(title_pool)
                company_tier = random.choice(["small", "medium", "large"])
        else:
            title_pool_1 = ALLOWED_TRANSITIONS[prev_experience["title"]] 
            title_pool_2 = TITLES_CAREER_STAGES[career_stage]
            title_pool = list(set(title_pool_1).intersection(title_pool_2)) or title_pool_1
            title = random.choice(title_pool)
            company_tier = random.choice(["small", "medium", "large"])

        # Default time ranges based on career stage if not specified
        if not start_year_range:
            if career_stage == "early":
                start_year_range = (2018, 2023)
            elif career_stage == "mid":
                start_year_range = (2015, 2020)
            elif career_stage == "senior":
                start_year_range = (2010, 2018)
            else:  # executive
                start_year_range = (2005, 2015)
        
        # Generate the experience
        return {
            "title": title,
            "company": self.generate_company(tier=company_tier),
            "description": f"Worked on various projects as a {title}.",
            "location": self.generate_location(),
            "timePeriod": self.generate_time_period(start_year_range=start_year_range, current=current),
            "entityUrn": f"urn:li:fs_experience:{random.randint(10000000, 99999999)}"
        }
    
    def generate_education(self, 
                         graduation_year_range: Tuple[int, int] = (2000, 2025),
                         tier: Optional[str] = None,
                         type: Optional[str] = "bachelors", # "bachelors", "masters", "phd"
                         field: Optional[str] = None # field of study
                         ) -> Dict[str, Any]:
        """
        Generate a realistic education entry.
        
        Args:
            graduation_year_range: Range for graduation year
            tier: Optional preference for university tier ('top', 'high', 'mid')
            
        Returns:
            Education data dictionary
        """
        # Select university based on tier
        if tier:
            filtered_unis = [u for u in self.universities if u["tier"] == tier]
            university = random.choice(filtered_unis or self.universities)
        else:
            university = random.choice(self.universities)
        
        # Calculate typical 4-year degree
        grad_year = random.randint(*graduation_year_range)
        start_year = grad_year - 4
        
        degree_types = ["Bachelor of Science", "Bachelor of Arts"] if type == "bachelors" else \
                        ["Master of Science", "Master of Arts"] if type == "masters" else \
                        ["PhD"]
        
        fields = DEGREE_FIELDS
        
        return {
            "school": {
                "schoolName": university["name"],
                "schoolUrn": university["urn"],
                "logo_url": university["logo_url"],
                "active": True
            },
            "degreeName": random.choice(degree_types),
            "fieldOfStudy": random.choice(fields) if not field else field,
            "timePeriod": {
                "startDate": {
                    "year": start_year,
                    "month": 9  # September typical start
                },
                "endDate": {
                    "year": grad_year,
                    "month": 6  # June typical graduation
                }
            },
            "entityUrn": f"urn:li:fs_education:{random.randint(10000000, 99999999)}"
        }
    
    def generate_skills(self, num_skills: int = 8, skill_ratio = 0.75) -> List[Dict[str, str]]:
        """Generate a list of skills for the profile."""

        tech_count = int(num_skills * skill_ratio)  # base 75% technical
        soft_count = num_skills - tech_count
        
        skills = []
        # are these ensured to not be the same when they're sampled? 
        skills.extend([{"name": skill} for skill in random.sample(TECH_SKILLS, min(tech_count, len(TECH_SKILLS)))])
        skills.extend([{"name": skill} for skill in random.sample(SOFT_SKILLS, min(soft_count, len(SOFT_SKILLS)))])
        
        return skills
    
    def generate_career_trajectory(self, 
                                num_positions: int = 3,
                                career_progression: Optional[List[str]] = None,
                                education_field: Optional[str] = None # field of study for education
                                ) -> List[Dict[str, Any]]:
        """
        Generate a realistic career trajectory with multiple positions.
        
        Args:
            num_positions: Number of positions to generate
            career_progression: Optional list of career stages (e.g., ["early", "mid", "senior"])
            
        Returns:
            List of experience entries in reverse chronological order
        """
        experiences = []
        
        # Default career progression if not specified
        if not career_progression:
            if num_positions == 1:
                career_progression = ["mid"]
            elif num_positions == 2:
                career_progression = ["early", "mid"]
            elif num_positions == 3:
                career_progression = ["early", "mid", "senior"]
            elif num_positions == 4:
                career_progression = ["early", "early", "mid", "senior"]
            else:
                # For larger trajectories, create a realistic progression
                career_progression = (
                    ["early"] * (num_positions // 3) +
                    ["mid"] * (num_positions // 3) +
                    ["senior"] * (num_positions // 3)
                )
                # Add remaining positions
                remaining = num_positions - len(career_progression)
                career_progression.extend(["executive"] * remaining)
        
        # Ensure career_progression has enough stages
        while len(career_progression) < num_positions:
            career_progression.append(career_progression[-1])
        
        # Generate experiences in chronological order (oldest first)
        start_year = 2005
        for i in range(num_positions):
            stage = career_progression[i]
            # Each position starts after the previous one
            start_year_range = (start_year, start_year + 3)
            
            # only set current to true if it's the last position
            exp = self.generate_experience(career_stage=stage,
                                            start_year_range=start_year_range,current = (i == num_positions - 1),
                                            prev_experience = experiences[-1] if experiences else None, 
                                            education_field = education_field)
            
            # Update start_year for next position
            if "endDate" in exp["timePeriod"]:
                start_year = exp["timePeriod"]["endDate"]["year"]
            else:
                # If current position, make it actually the last 1-2 years
                current_year = datetime.now().year
                exp["timePeriod"]["startDate"]["year"] = max(exp["timePeriod"]["startDate"]["year"], current_year - 2)
                start_year = current_year
            
            experiences.append(exp)
        
        # Return in reverse chronological order (newest first)
        return experiences[::-1]
    
    
    def generate_profile(self, 
                       
                       career_length : str = "mid",  # "early", "mid", "senior", "executive" 
                       education_level: str = "bachelors",  # "bachelors", "masters", "phd"
                       tier: Optional[str] = None, # "mid", "high", "top"
                       num_skills: int = 8,
                       force:bool = False) -> Dict[str, Any]:
        """
        Generate a complete profile with realistic data based on specified parameters.
        
        Args:
            career_length: Length/seniority of career to generate
            education_level: Level of education to generate
            num_skills: Number of skills to generate
            force: If True, generate a profile that ignores probabilities and generates a profile with specified career length
            
        Returns:
            Complete LinkedIn profile data
        """
        # Generate a unique profile ID
        profile_id = str(random.randint(10000000, 99999999))
        # ensure that profile_id is not already in use
        while profile_id in [profile["profile_id"] for profile in self.profiles]:
            profile_id = str(random.randint(10000000, 99999999))
            
        
        urn_id = f"ACoAAC{profile_id}"
        profile_urn = f"urn:li:fs_profile:{urn_id}"
        
        # Generate name
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)


        # Generate education based on level
        education = []
        if education_level == "bachelors":
            education.append(self.generate_education(
                graduation_year_range=(2005, 2020),
                tier=tier,
                type="bachelors"

            ))
        elif education_level == "masters":
            # Undergraduate degree
            undergrad = self.generate_education(
                graduation_year_range=(2005, 2018),
                tier=random.choice(["mid", "high", "top"]),
                type="bachelors"
            )
            
            # Graduate degree, starting after undergrad
            grad_start_year = undergrad["timePeriod"]["endDate"]["year"]
            masters = self.generate_education(
                graduation_year_range=(grad_start_year + 1, grad_start_year + 3),
                tier=random.choice(["high", "top"]),
                type="masters"
            )
            
            education = [masters, undergrad]  # Newest first
        elif education_level == "phd":
            # Undergraduate degree
            undergrad = self.generate_education(
                graduation_year_range=(2000, 2015),
                tier=random.choice(["mid","high", "top"]),
                type="bachelors"
            )
            # 40% chance of having a Masters, starting after undergrad
            if random.random() < 0.4:
                grad_start_year = undergrad["timePeriod"]["endDate"]["year"]
                masters = self.generate_education(
                    graduation_year_range=(grad_start_year + 1, grad_start_year + 3),
                    tier=random.choice(["high", "top"]),
                    type="masters"
                )
                education = [masters, undergrad]
            else:
                education = [undergrad]

            # PhD, starting after undergrad
            grad_start_year = education[-1]["timePeriod"]["endDate"]["year"]
            phd = self.generate_education(
                graduation_year_range=(grad_start_year + 4, grad_start_year + 7),
                tier=random.choice(["high", "top"]),
                type="phd"
            )
            
            education.append(phd)  
            # inverse order
            education = education[::-1]
        
        # generate experience tier based on education level
        # score = sum of education * tier, where tier is 1, 2, 3 for mid, high, top
        # education is 1, 2, 3 for bachelors, masters, phd
        # score = Sum of tier * education for all education experiences  = 1 * 1 + 1 * 2 = 3
        # career length/ tier is based on score
        total_score = 0
        for edu in education:
            score = 0
            print("degree", edu["degreeName"])
            if "Bachelor" in edu["degreeName"]:
                score += 1
            elif "Master" in edu["degreeName"]:
                score += 2
            elif "PhD" in edu["degreeName"]:
                score += 3
            print("score p1", score)
            print("school",edu["school"])
            if edu["school"]["schoolName"] in {university["name"] for university in UNIVERSITIES}:
                tier = {university["name"]:university["tier"] for university in UNIVERSITIES}[edu["school"]["schoolName"]]
                print("tier", tier)
                if tier == "mid":
                    score *= 1
                elif tier == "high":
                    score *= 2
                elif tier == "top":
                    score *= 3
            print("score p2", score)
            total_score += score

        print("total score",total_score)

        # sub function to get career config based on career length
        def get_stochastic_career_config(career_length):
            """Generate career configuration based on career length with stochastic position counts."""
            
            # Determine position count based on career length with some randomness
            if career_length == "early":
                positions = max(1, min(4, int(random.normalvariate(2, 0.8))))
            elif career_length == "mid":
                positions = max(2, min(6, int(random.normalvariate(3, 1.0))))
            elif career_length == "senior":
                positions = max(4, min(8, int(random.normalvariate(4, 1.2))))
            else:  # executive
                positions = max(5, min(10, int(random.normalvariate(6, 1.5))))
            
            # Build progression array based on position count
            if career_length == "early":
                progression = ["early"] * positions
            elif career_length == "mid":
                early_count = min(positions - 1, max(1, int(positions * 0.6)))
                progression = ["early"] * early_count + ["mid"] * (positions - early_count)
            elif career_length == "senior":
                early_count = min(positions - 2, max(1, int(positions * 0.4)))
                mid_count = min(positions - early_count - 1, max(1, int(positions * 0.4)))
                progression = ["early"] * early_count + ["mid"] * mid_count + ["senior"] * (positions - early_count - mid_count)
            else:  # executive
                early_count = min(positions - 3, max(1, int(positions * 0.3)))
                mid_count = min(positions - early_count - 2, max(1, int(positions * 0.3)))
                senior_count = min(positions - early_count - mid_count - 1, max(1, int(positions * 0.3)))
                progression = ["early"] * early_count + ["mid"] * mid_count + ["senior"] * senior_count + ["executive"] * (positions - early_count - mid_count - senior_count)
            
            return {"positions": positions, "progression": progression}

        # add influence from education to career length
        if total_score <= 3:
            education_based_length = random.choices(["early", "mid","senior"], weights=[0.65, 0.25,0.1])[0]
        elif total_score <= 6:
            education_based_length = random.choices(["early","mid", "senior"], weights=[0.2,0.5, 0.3])[0]
        elif total_score <= 9:
            education_based_length = random.choices(["mid","senior", "executive"], weights=[0.3,0.6, 0.1])[0]
        else:
            education_based_length = random.choices(["senior", "executive"], weights=[0.8, 0.2])[0]
        
        # Randomly choose between career length and education based length
        career_length = career_length or education_based_length

        print(career_length)
        # Map career length to number of positions and progression
        config = get_stochastic_career_config(career_length)
        
        print(config)
        # Generate career trajectory
        experiences = self.generate_career_trajectory(
            num_positions=config["positions"],
            career_progression=config["progression"], 
            education_field = education[0]["fieldOfStudy"] if education else None,
        )

        
        # Current position from most recent experience
        current_position = experiences[0]["title"] if experiences else "Professional"
        current_company = experiences[0]["company"]["companyName"] if experiences else ""
        
        # Create the complete profile
        profile_data = {
            "profile_id": profile_id,
            "profile_urn": profile_urn,
            "member_urn": f"urn:li:member:{profile_id}",
            "public_id": f"{first_name.lower()}-{last_name.lower()}-{profile_id[:4]}",
            "firstName": first_name,
            "lastName": last_name,
            "headline": f"{current_position} at {current_company}" if current_company else current_position,
            "summary": f"Experienced {current_position} with a passion for technology and innovation.",
            "industryName": "Computer Software" if "software" in current_position.lower() else "Information Technology",
            "locationName": experiences[0]["location"]["locationName"] if experiences else "San Francisco, CA",
            "geoCountryName": "United States",
            "experience": experiences,
            "education": education,
            "skills": self.generate_skills(num_skills),
            "projects": [],
            "urn_id": urn_id
        }
        
        # Store the profile for future reference
        self.profiles.append(profile_data)
        
        return profile_data
    
    def generate_job_transition(self, 
                              profile: Dict[str, Any],
                              transition_type: str = "company_change",  # company_change, promotion
                              transition_date: Optional[datetime] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate a job transition for an existing profile.
        
        Args:
            profile: Existing profile to generate transition for
            transition_type: Type of transition to generate
            transition_date: Optional specific date for the transition
            
        Returns:
            Tuple of (updated profile, transition event)
        """
        # Make a deep copy to avoid modifying the original
        updated_profile = copy.deepcopy(profile)
        
        # Default transition date if not specified
        if not transition_date:
            transition_date = datetime.now() - timedelta(days=random.randint(30, 180))
        
        # Get the current/most recent experience
        if not updated_profile["experience"]:
            raise ValueError("Profile has no experience entries")
        
        # TODO: might need to change this to get the most recent experience
        old_experience = updated_profile["experience"][0]
        
        # Create a new experience based on transition type
        if transition_type == "company_change":
            # Change to a new company
            new_company = self.generate_company()
            while new_company["companyName"] == old_experience["company"]["companyName"]:
                new_company = self.generate_company()
            new_title = random.choice(ALLOWED_TRANSITIONS[old_experience["title"]])
                
            new_experience = {
                "title": new_title,  # Same title, new company
                "company": new_company,
                "description": f"Joined {new_company['companyName']} as a {new_title}.",
                "location": self.generate_location(),
                "timePeriod": {
                    "startDate": {
                        "year": transition_date.year,
                        "month": transition_date.month
                    }
                },
                "entityUrn": f"urn:li:fs_experience:{random.randint(10000000, 99999999)}"
            }
            
        elif transition_type == "promotion":
            # Promotion at the same company
            current_title = old_experience["title"]
            new_title = random.choice(ALLOWED_TRANSITIONS[current_title])
            
            new_experience = {
                "title": new_title,
                "company": old_experience["company"],  # Same company
                "description": f"Promoted to {new_title} at {old_experience['company']['companyName']}.",
                "location": old_experience["location"],  # Same location
                "timePeriod": {
                    "startDate": {
                        "year": transition_date.year,
                        "month": transition_date.month
                    }
                },
                "entityUrn": f"urn:li:fs_experience:{random.randint(10000000, 99999999)}"
            }
        
        # Close out the old experience with an end date
        if "endDate" not in old_experience["timePeriod"]:
            old_experience["timePeriod"]["endDate"] = {
                "year": transition_date.year,
                "month": transition_date.month
            }
        
        # Insert the new experience at the beginning
        updated_profile["experience"].insert(0, new_experience)
        
        # Update headline if it's a company change or promotion
        if transition_type in ["company_change", "promotion"]:
            updated_profile["headline"] = f"{new_experience['title']} at {new_experience['company']['companyName']}"
        
        # Create the transition event object compatible with your model
        transition_event = self.generate_transition_event(
            transition_date=transition_date,
            profile=updated_profile,
            old_experience=old_experience,
            new_experience=new_experience,
            transition_type=transition_type,
        )
        
        return updated_profile, transition_event
    
    def generate_transition_event(self,
                                  
                                transition_date: datetime,
                                profile: Dict[str, Any],
                                old_experience: Dict[str, Any],
                                new_experience: Dict[str, Any],
                                transition_type: str) -> TransitionEvent:
        """
        Generate a transition event object for a job change or promotion.


        Args:

            transition_date: Date of the transition
            profile: Updated profile after the transition
            old_experience: Previous experience entry
            new_experience: New experience entry
            transition_type: Type of transition (company_change, promotion)

        Returns:
            Transition event dictionary
        """
        return TransitionEvent(**{
            "transition_date": transition_date.isoformat(),
            "profile_urn": profile["profile_urn"],
            "from_company_urn": old_experience["company"]["companyUrn"],
            "to_company_urn": new_experience["company"]["companyUrn"],
            "transition_type": transition_type,
            "old_title": old_experience["title"],
            "new_title": new_experience["title"],
            "location_change": old_experience["location"]["locationName"] != new_experience["location"]["locationName"],
            "tenure_days": abs(transition_date - datetime(
                old_experience["timePeriod"]["startDate"]["year"],
                old_experience["timePeriod"]["startDate"]["month"],
                1
            )).days
        })
    # ______________________________________________________
    # mass generation functions for creating realistic mock data
    # ______________________________________________________
    def generate_profile_dataset(self, 
                               size: int = 100, 
                               career_distribution: Optional[Dict[str, float]] = None,
                               education_distribution: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Generate a dataset of profiles with realistic distributions.
        
        Args:
            size: Number of profiles to generate
            career_distribution: Optional distribution of career lengths (e.g. {"early": 0.3, "mid": 0.4, "senior": 0.2, "executive": 0.1})
            education_distribution: Optional distribution of education levels
            
        Returns:
            List of profile dictionaries
        """
        # Default distributions if not specified
        if not career_distribution:
            career_distribution = {
                "early": 0.3,    # 30% early career
                "mid": 0.4,      # 40% mid career
                "senior": 0.2,   # 20% senior
                "executive": 0.1  # 10% executive
            }
        
        if not education_distribution:
            education_distribution = {
                "bachelors": 0.6,  # 60% bachelors only
                "masters": 0.3,    # 30% masters
                "phd": 0.1        # 10% PhD
            }
        
        # Create weighted choices
        career_choices = [k for k, v in career_distribution.items() for _ in range(int(v * 100))]
        education_choices = [k for k, v in education_distribution.items() for _ in range(int(v * 100))]
        
        profiles = []
        for _ in range(size):
            career_length = random.choice(career_choices)
            education_level = random.choice(education_choices)
            
            profile_data = self.generate_profile(
                career_length=career_length,
                education_level=education_level,
                num_skills=random.randint(5, 12)
            )
            
            profiles.append(profile_data)
        
        return profiles
    def generate_existing_transition_dataset(self) -> List[Dict[str, Any]]:
        """
       Generate job transition events data from existing profile transition data.

        Returns:
            List of transition events
        """
        transitions = []
        for profile in self.profiles:
            # go through experiences of each profile and generate transition events
            for i in range(len(profile["experience"]) - 1, -1, -1):
                if i == 0:
                    continue
                old_experience = profile["experience"][i]
                new_experience = profile["experience"][i-1]
                transition_date = datetime(new_experience["timePeriod"]["startDate"]["year"], new_experience["timePeriod"]["startDate"]["month"], 1)
                transition_type = "company_change" if old_experience["company"]["companyName"] != new_experience["company"]["companyName"] else "promotion"
                
                transition = self.generate_transition_event(
                    transition_date=transition_date,
                    profile=profile,
                    old_experience=old_experience,
                    new_experience=new_experience,
                    transition_type=transition_type
                )

                transitions.append(transition)

        return transitions


    def generate_new_transition_data(self, 
                                 profiles: List[Dict[str, Any]], 
                                 transition_rate: float = 0.3,
                                 transition_distribution: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Generate job transitions for a set of profiles,
        and set the DataGenerator's profiles field to the new profiles w/ updates
        
        Args:
            profiles: List of profiles to generate transitions for
            transition_rate: Fraction of profiles that should have transitions
            transition_distribution: Optional distribution of transition types
            
        Returns:
            List of transition events
        """
        # Generate all transitions from existing profiles

        if not transition_distribution:
            transition_distribution = {
                "company_change": 0.6,  # 60% company changes
                "promotion": 0.4,       # 30% promotions
            }
        
        # Create weighted choices
        transition_choices = [k for k, v in transition_distribution.items() for _ in range(int(v * 100))]
        
        # Determine which profiles will have transitions
        transition_count = int(len(profiles) * transition_rate)
        transition_profiles = random.sample(profiles, transition_count)
        
        transitions = []
        updated_profiles = []
        
        for profile in profiles:
            if profile in transition_profiles:
                transition_type = random.choice(transition_choices)
                
                # Generate random date in last 6-48 months after starting last job
                days_ago = random.randint(180, 1460)
                start_date = datetime(profile["experience"][0]["timePeriod"]["startDate"]["year"], profile["experience"][0]["timePeriod"]["startDate"]["month"], 1)

                transition_date = start_date + timedelta(days=days_ago)
                
                try:
                    updated_profile, transition = self.generate_job_transition(
                        profile=profile,
                        transition_type=transition_type,
                        transition_date=transition_date
                    )
                    
                    transitions.append(transition)
                    updated_profiles.append(updated_profile)
                except ValueError:
                    # Skip if profile has no experience
                    updated_profiles.append(profile)
            else:
                updated_profiles.append(profile)
        
        # Replace the original profiles with updated ones
        self.profiles = updated_profiles
        
        return transitions
    
    def generate_company_dataset(self) -> List[Dict[str, Any]]:
        """
        Generate complete LinkedIn company objects for all companies in the dataset.
        
        Returns:
            List of LinkedIn company objects
        """
        company_dataset = []
        
        for company in self.companies:
            # Create a more complete company object
            company_size = company["size"]
            industry = company["industry"]
            
            # Generate follower count based on company size
            follower_ranges = {
                "small": (100, 5000),
                "medium": (5000, 100000),
                "large": (100000, 5000000)
            }
            follower_range = follower_ranges.get(company_size, (100, 5000))
            follower_count = random.randint(*follower_range)
            
            # Staff count based on company size
            staff_ranges = {
                "small": (10, 200),
                "medium": (201, 5000),
                "large": (5001, 100000)
            }
            staff_range = staff_ranges.get(company_size, (10, 200))
            staff_count = random.randint(*staff_range)
            
            company_data = {
                "name": company["name"],
                "tagline": f"Leading {industry} company",
                "description": f"{company['name']} is a {company_size} {industry} company focused on innovation and growth.",
                "entityUrn": company["urn"],
                "universalName": company["name"].lower().replace(" ", ""),
                "companyPageUrl": f"https://www.linkedin.com/company/{company['name'].lower().replace(' ', '-')}",
                "url": f"https://www.{company['name'].lower().replace(' ', '')}.com",
                "staffingCompany": False,
                "companyIndustries": [
                    {
                        "localizedName": industry,
                        "entityUrn": f"urn:li:fs_industry:{random.randint(10000, 99999)}"
                    }
                ],
                "staffCount": staff_count,
                "staffCountRange": company["employee_range"],
                "permissions": {
                    "landingPageAdmin": False,
                    "admin": False,
                    "adAccountHolder": False
                },
                "logo": {
                    "image": {
                        "com.linkedin.common.VectorImage": {
                            "artifacts": [
                                {
                                    "width": 200,
                                    "height": 200,
                                    "fileIdentifyingUrlPathSegment": f"{company['name'].lower().replace(' ', '_')}_200.png",
                                    "expiresAt": int(datetime.now().timestamp() + 86400 * 30)
                                }
                            ],
                            "rootUrl": "https://media.licdn.com/dms/image/company-logos/"
                        }
                    }
                },
                "followingInfo": {
                    "entityUrn": f"urn:li:fs_followingInfo:{random.randint(10000000, 99999999)}",
                    "dashFollowingStateUrn": f"urn:li:fs_followingState:{random.randint(10000000, 99999999)}",
                    "following": False,
                    "followingType": "DEFAULT",
                    "followerCount": follower_count
                },
                "companyType": {
                    "localizedName": "Company",
                    "code": "C"
                }
            }
            
            # Add funding data only for startups
            if company_size == "small" and random.random() < 0.7:
                funding_data = {
                    "fundingRoundListCrunchbaseUrl": f"https://www.crunchbase.com/organization/{company['name'].lower().replace(' ', '-')}/funding_rounds",
                    "lastFundingRound": {
                        "investorsCrunchbaseUrl": f"https://www.crunchbase.com/funding_round/company-series-a",
                        "leadInvestors": [
                            {
                                "name": {"en": "Venture Partners"},
                                "investorCrunchbaseUrl": "https://www.crunchbase.com/organization/venture-partners",
                                "image": None
                            }
                        ],
                        "fundingRoundCrunchbaseUrl": f"https://www.crunchbase.com/funding_round/{company['name'].lower().replace(' ', '-')}-series-a",
                        "fundingType": "Series A",
                        "moneyRaised": {
                            "currencyCode": "USD",
                            "amount": str(random.randint(2, 20) * 1000000)
                        },
                        "numOtherInvestors": random.randint(1, 5),
                        "announcedOn": {
                            "year": datetime.now().year - random.randint(0, 3),
                            "month": random.randint(1, 12),
                            "day": random.randint(1, 28)
                        }
                    },
                    "companyCrunchbaseUrl": f"https://www.crunchbase.com/organization/{company['name'].lower().replace(' ', '-')}",
                    "numFundingRounds": random.randint(1, 3),
                    "updatedAt": int(datetime.now().timestamp() - random.randint(0, 86400 * 30))
                }
                company_data["fundingData"] = funding_data
            
            company_dataset.append(company_data)
        
        return company_dataset
    
    def to_pydantic_models(self, profile_data: Dict[str, Any]) -> LinkedInProfile:
        """
        Convert a profile dictionary to a LinkedInProfile Pydantic model.
        
        Args:
            profile_data: Profile data dictionary
            
        Returns:
            LinkedInProfile Pydantic model instance
        """
        try:
            profile = LinkedInProfile(**profile_data)
            return profile
        except ValidationError as e:
            print(f"Error creating LinkedIn profile model: {e}")
            raise
    
    def create_and_save_mock_dataset(self, 
                                   num_profiles: int = 100,
                                   transition_rate: float = 0.3,
                                   output_dir: str = "mock_data") -> Dict[str, List]:
        """
        Generate a complete mock dataset and save to JSON files.
        
        Args:
            num_profiles: Number of profiles to generate
            transition_rate: Fraction of profiles with job transitions
            output_dir: Directory to save output files
            
        Returns:
            Dictionary with lists of generated data
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate profiles
        profiles = self.generate_profile_dataset(size=num_profiles)
        
        # Generate transitions
        transitions = self.generate_existing_transition_dataset(
        )
        
        # Generate companies
        companies = self.generate_company_dataset()
        
        # Convert to Pydantic models
        pydantic_profiles = []
        for profile_data in profiles:
            try:
                profile = self.to_pydantic_models(profile_data)
                pydantic_profiles.append(profile)
            except Exception as e:
                print(f"Error converting profile to Pydantic model: {e}")
        
        # Save to JSON files
        with open(f"{output_dir}/profiles.json", "w") as f:
            json.dump(profiles, f, indent=2)
        
        with open(f"{output_dir}/transitions.json", "w") as f:
            json.dump(transitions, f, indent=2)
        
        with open(f"{output_dir}/companies.json", "w") as f:
            json.dump(companies, f, indent=2)
        
        return {
            "profiles": profiles,
            "transitions": transitions,
            "companies": companies,
            "pydantic_profiles": pydantic_profiles
        }
    


def generate_mock_data_for_testing(num_profiles: int = 100, output_dir: str = "mock_data") -> None:
    """Convenience function to generate a complete mock dataset for testing."""
    generator = LinkedInDataGenerator()
    dataset = generator.create_and_save_mock_dataset(
        num_profiles=num_profiles,
        transition_rate=0.3,
        output_dir=output_dir
    )
    
    print(f"Generated {len(dataset['profiles'])} profiles")
    print(f"Generated {len(dataset['transitions'])} transitions")
    print(f"Generated {len(dataset['companies'])} companies")
    
    return dataset
        
if __name__ == "__main__":
    pass
    # leave this empty until we want to utilize file. 