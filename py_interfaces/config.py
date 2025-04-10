# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "5001"))

# LinkedIn API settings
LINKEDIN_USER = os.getenv("LINKEDIN_USER_1")
LINKEDIN_PASS = os.getenv("LINKEDIN_PASS_1")

# Neo4j settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")

# Druid settings
DRUID_INGEST_URL = os.getenv("DRUID_INGEST_URL")
DRUID_USER = os.getenv("DRUID_USER")
DRUID_PASSWORD = os.getenv("DRUID_PASSWORD")

# Proxy settings
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
PROXY_URL = os.getenv("PROXY_URL")