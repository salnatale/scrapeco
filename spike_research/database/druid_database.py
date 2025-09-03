import json
import os
from datetime import datetime

import requests

# load environment variables
from dotenv import load_dotenv

from ..core.models import Company, Employee, Experience, TimePeriod  # Pydantic models


load_dotenv(override=True)
# load DRUID_INGEST_URL from environment variables
DRUID_INGEST_URL = os.getenv("DRUID_INGEST_URL")
HEADERS = {"Content-Type": "application/json"}
AUTH = (
    os.getenv("DRUID_USER"),  # From environment variables
    os.getenv("DRUID_PASSWORD"),  # From environment variables
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
                    "rollup": False,
                },
            },
            "ioConfig": {
                "type": "index_parallel",
                "inputSource": {"type": "inline", "data": ""},
                "inputFormat": {"type": "json"},
                "appendToExisting": False,
            },
        },
    }


def send_to_druid(profiles: list[Employee], companies: list[Company]):
    """Serialize Pydantic models and ingest into Druid"""

    # Convert Pydantic models to JSON strings
    profile_data = "\n".join([p.model_dump_json() for p in profiles])
    company_data = "\n".join([c.model_dump_json() for c in companies])

    # Create separate ingestion tasks
    for data, source_name in [
        (profile_data, "linkedin_profiles"),
        (company_data, "linkedin_companies"),
    ]:
        spec = create_ingestion_spec(source_name)
        spec["spec"]["ioConfig"]["inputSource"]["data"] = data

        response = requests.post(
            DRUID_INGEST_URL,
            json=spec,
            headers=HEADERS,
            auth=AUTH,  # Replace with your credentials (auth,auth for development)
        )

        if response.status_code == 200:
            print(f"Successfully initiated ingestion for {source_name}")
        else:
            print(f"Failed to ingest {source_name}: {response.text}")


# # Usage
# profiles = [Employee(...)]  # parsed profiles
# companies = [Company(...)] # parsed companies
# send_to_druid(profiles, companies)


def query_druid(query: dict) -> dict:
    """Query Druid"""
    response = requests.post(DRUID_INGEST_URL, json=query, headers=HEADERS, auth=AUTH)
    return response.json()


def create_transition_event(
    profile: Employee,
    old_experience: Experience,
    new_experience: Experience,
    transition_date: datetime,
    transition_type: str = "role_change",
) -> dict:
    """
    Creates a structured transition event for Druid ingestion.
    """
    transition_event = {
        "transition_date": transition_date.isoformat(),
        "profile_urn": profile.profile_urn,
        "from_company_urn": old_experience.company.urn,
        "to_company_urn": new_experience.company.urn,
        "transition_type": transition_type,
        "old_title": old_experience.title,
        "new_title": new_experience.title,  # Add new title tracking
        "location_change": old_experience.location.name != new_experience.location.name
        if (old_experience.location and new_experience.location)
        else False,
        "tenure_days": (
            transition_date - get_start_date(old_experience.time_period)
        ).days,  # Compute tenure
    }
    return transition_event


def get_start_date(time_period: TimePeriod):
    """Extracts the start date in datetime format from a TimePeriod object"""
    start_date = time_period.start_date  # Correct key
    return datetime(
        start_date["year"], start_date["month"], 1
    )  # Create from start data


def send_transition_update(transition_event: dict) -> bool:
    """
    Sends an employee transition event to Druid for ingestion.
    """
    with open("data_schema/druid_transmission_schema.json") as f:
        ingestion_spec = json.load(f)

    ingestion_spec["spec"]["ioConfig"]["inputSource"]["data"] = json.dumps(
        transition_event
    )

    response = requests.post(
        DRUID_INGEST_URL, json=ingestion_spec, headers=HEADERS, auth=AUTH
    )

    if response.status_code == 200:
        print(f"Successfully sent transition event: {transition_event['profile_urn']}")
        return True
    else:
        print(f"Error sending transition: {response.status_code} - {response.text}")
        return False
