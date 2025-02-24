import requests
from models import LinkedInProfile, LinkedInCompany  # Pydantic models
import os
from typing import List
# load DRUID_INGEST_URL from environment variables
DRUID_INGEST_URL = os.getenv("DRUID_INGEST_URL")
HEADERS = {"Content-Type": "application/json"}
AUTH = (
    os.getenv("DRUID_USER"),       # From environment variables
    os.getenv("DRUID_PASSWORD")   # From environment variables
)

def create_ingestion_spec(data_source: str) -> dict:
    """Create a native batch ingestion spec template"""
    return {
        "type": "index_parallel",
        "spec": {
            "dataSchema": {
                "dataSource": data_source,
                "timestampSpec": {"column": "timestamp", "format": "auto"},
                "dimensionsSpec": {"useSchemaDiscovery": True},
                "granularitySpec": {
                    "segmentGranularity": "day",
                    "queryGranularity": "none",
                    "rollup": False
                }
            },
            "ioConfig": {
                "type": "index_parallel",
                "inputSource": {"type": "inline", "data": ""},
                "inputFormat": {"type": "json"},
                "appendToExisting": False
            }
        }
    }

def send_to_druid(profiles: List[LinkedInProfile], companies: List[LinkedInCompany]):
    """Serialize Pydantic models and ingest into Druid"""
    
    # Convert Pydantic models to JSON strings
    profile_data = "\n".join([p.json() for p in profiles])
    company_data = "\n".join([c.json() for c in companies])
    
    # Create separate ingestion tasks
    for data, source_name in [(profile_data, "linkedin_profiles"), 
                             (company_data, "linkedin_companies")]:
        spec = create_ingestion_spec(source_name)
        spec["spec"]["ioConfig"]["inputSource"]["data"] = data
        
        response = requests.post(
            DRUID_INGEST_URL,
            json=spec,
            headers=HEADERS,
            auth=AUTH # Replace with your credentials (auth,auth for development)
        )
        
        if response.status_code == 200:
            print(f"Successfully initiated ingestion for {source_name}")
        else:
            print(f"Failed to ingest {source_name}: {response.text}")

# # Usage
# profiles = [LinkedInProfile(...)]  # parsed profiles
# companies = [LinkedInCompany(...)] # parsed companies
# send_to_druid(profiles, companies)
