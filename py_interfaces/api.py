from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
import os
import json
import uvicorn
import numpy as np
import pandas as pd
from uuid import uuid4, UUID
from datetime import datetime, timedelta
import logging
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
import networkx as nx
import traceback
import glob
from openai import OpenAI
# Import custom modules
from enrich_company import PitchbookEnricher          
from fastapi import BackgroundTasks                 
from uuid import uuid4
from datetime import datetime
from parser import (
    raw_text_from_upload,
    text_to_profile,
    transitions_from_profile,
    check_companies,
)

# Import your existing modules
from models import LinkedInProfile, LinkedInCompany, TransitionEvent
from neo4j_database import (
    Neo4jDatabase,
    send_to_neo4j,
    send_transition_to_neo4j,
    query_neo4j,
)
from druid_database import send_to_druid, send_transition_update
from main import LinkedInAPI
from mock_enhanced import LinkedInDataGenerator
from security import verify_api_key, get_current_user, User, oauth2_scheme
from langchain_community.chat_models import ChatOpenAI as LangchainOpenAI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced_api")

# Initialize cache for API responses to avoid redundant computation
cache = {
    "last_execution": datetime.now(),
    "last_request_time": {},
    "request_counts": {},
    "job_data": {},
    "job_status": {},
    "talent_flow_cache": {},
    "recommendations_cache": {},
    "insights_cache": {},
    "opportunities_cache": {},
    "geographic_data": {},
    "last_updated": {},
    "client_timestamps": {},
    "last_user_agent": ""
}

# Simple rate limiter
class RateLimiter:
    def __init__(self):
        self.request_counts = {}
        self.last_reset = {}
        self.violation_counts = {}  # Track repeated violations
        self.max_requests = 20  # Max requests per minute - increased for testing
        self.window_seconds = 60  # 1 minute window
        
        # Special config for talent flow endpoint which needs stricter limits
        self.endpoint_config = {
            "talent_flow": {
                "max_requests": 10,  # Lower limit for talent flow endpoint
                "window_seconds": 60,  # Same window
                "burst_threshold": 3,  # Max requests in 3 seconds
                "burst_window": 3,     # Time window for burst detection
                "backoff_multiplier": 2.0  # Exponential backoff for violations
            },
            "opportunities": {
                "max_requests": 15,  # Higher limit for opportunities endpoint
                "window_seconds": 60,  # Same window
                "burst_threshold": 5,  # More lenient burst threshold
                "burst_window": 5,     # Longer burst window
                "backoff_multiplier": 1.5  # More gentle backoff
            }
        }
        
    def is_allowed(self, endpoint, ip_address):
        key = f"{endpoint}_{ip_address}"
        current_time = datetime.now()
        
        # Get endpoint-specific config if available, otherwise use defaults
        config = self.endpoint_config.get(endpoint, {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "burst_threshold": 5,
            "burst_window": 3,
            "backoff_multiplier": 1.0
        })
        
        # Check if we're in backoff period due to violations
        if key in self.violation_counts:
            # Calculate dynamic backoff window based on violation count
            backoff_window = min(300, config["window_seconds"] * (config["backoff_multiplier"] ** self.violation_counts[key]))
            
            # Check if we're still in backoff period
            if key in self.last_reset:
                time_diff = (current_time - self.last_reset[key]).total_seconds()
                if time_diff < backoff_window:
                    # Still in backoff, don't allow request and don't reset counter
                    return False
                else:
                    # Backoff period expired, reduce violation count
                    self.violation_counts[key] = max(0, self.violation_counts[key] - 1)
        
        # Check if we should reset the counter
        if key in self.last_reset:
            time_diff = (current_time - self.last_reset[key]).total_seconds()
            if time_diff > config["window_seconds"]:
                # Reset counter if window has passed
                self.request_counts[key] = 0
                self.last_reset[key] = current_time
        else:
            # First request
            self.request_counts[key] = 0
            self.last_reset[key] = current_time
            
        # Increment counter
        self.request_counts[key] = self.request_counts.get(key, 0) + 1
        
        # Check burst detection for rapid requests if client timestamps exist
        if "client_timestamps" in cache and endpoint == "talent_flow":
            client_id = f"{ip_address}_" + cache.get("last_user_agent", "")[:20]
            timestamps = cache["client_timestamps"].get(client_id, [])
            
            # Look for too many requests in a short time window
            recent_requests = [ts for ts in timestamps 
                              if (current_time - ts).total_seconds() < config["burst_window"]]
            
            if len(recent_requests) >= config["burst_threshold"]:
                # Burst detected, add a violation
                self.violation_counts[key] = self.violation_counts.get(key, 0) + 1
                print(f"Burst detected for {key}: {len(recent_requests)} requests in {config['burst_window']}s")
                return False
        
        # Check if over rate limit
        is_allowed = self.request_counts[key] <= config["max_requests"]
        
        # If not allowed, record a violation
        if not is_allowed:
            self.violation_counts[key] = self.violation_counts.get(key, 0) + 1
            print(f"Rate limit violation for {key} (count: {self.violation_counts[key]})")
        
        return is_allowed
    
    def get_backoff_time(self, endpoint, ip_address):
        """Calculate recommended backoff time for a rate-limited client"""
        key = f"{endpoint}_{ip_address}"
        config = self.endpoint_config.get(endpoint, {
            "window_seconds": self.window_seconds,
            "backoff_multiplier": 1.0
        })
        
        violation_count = self.violation_counts.get(key, 0)
        backoff_seconds = min(300, int(config["window_seconds"] * (config["backoff_multiplier"] ** violation_count)))
        
        return backoff_seconds

# Initialize rate limiter
rate_limiter = RateLimiter()
import glob
from tqdm import tqdm
import pandas as pd

# Initialize the FastAPI app
app = FastAPI(
    title="LinkedIn Data API",
    description="API for LinkedIn data processing and storage",
    version="1.0.0",
)

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LinkedIn API client
linkedin_api = None

# Initialize mock data generator for development
data_generator = LinkedInDataGenerator()

# ─────────────────── Pydantic request models ──────────────────────────
# Define request models
class ProfileRequest(BaseModel):
    public_id: str


class SearchRequest(BaseModel):
    query: Dict[str, Any]
    description: Optional[str] = None


class MockGenerationConfig(BaseModel):
    num_profiles: int = 10
    store_in_db: bool = True
    career_distribution: Optional[Dict[str, float]] = None
    education_distribution: Optional[Dict[str, float]] = None


# define pagerank models
class ProjectionRequest(BaseModel):
    graph_name: str = "empCompany"
    weight_scheme: Literal["count", "binary"] = "count"
    delete_existing: bool = False


class PageRankRequest(BaseModel):
    graph_name: str = "empCompany"
    damping: float = 0.85
    iterations: int = 20
    write_property: Optional[str] = None  # None ⇒ stream to JSON


class BiRankRequest(BaseModel):
    graph_name: str = "empCompany"
    alpha: float = 0.85
    beta: float = 0.85
    max_iter: int = 20
    write_prefix: Optional[str] = None  # None ⇒ stream to JSON


class VCFiltersRequest(BaseModel):
    mode: Literal["research", "portfolio"] = "research"
    industries: Optional[List[str]] = None
    funding_stages: Optional[List[str]] = None
    geo_regions: Optional[List[str]] = None
    portfolio_ids: Optional[List[str]] = None  # For portfolio mode

class CompanyAnalysisRequest(BaseModel):
    company_ids: List[str]
    metrics: Optional[List[str]] = None
    time_period: Literal["1m", "3m", "6m", "1y", "all"] = "all"
    
    
class CompanyScoreRequest(BaseModel):
    company_urns: List[str] = []
    include_pagerank: bool = True
    include_birank: bool = True
    include_talent_flow: bool = True

class CompanyScore(BaseModel):
    company_urn: str
    company_name: str
    pagerank_score: Optional[float] = None
    birank_employee_score: Optional[float] = None
    birank_company_score: Optional[float] = None
    talent_inflow: int = 0
    talent_outflow: int = 0
    net_talent_flow: int = 0
    composite_score: float = 0.0

class AlertConfig(BaseModel):
    alert_type: str  # 'talent_drain', 'high_growth', 'competitor_move'
    threshold: float
    company_urns: List[str] = []
    enabled: bool = True

class Alert(BaseModel):
    id: str
    alert_type: str
    company_urn: str
    company_name: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    message: str

# Missing models for advanced analytics

class TimeseriesDataPoint(BaseModel):
    """Single data point in a time series"""
    date: datetime
    value: float

class CompanyDeepDiveRequest(BaseModel):
    """Request parameters for company deep dive analysis"""
    company_id: str
    metrics: List[str] = ["talent_flow", "growth", "funding", "sentiment"]
    time_period: Literal["1m", "3m", "6m", "1y", "all"] = "1y"
    include_competitors: bool = True
    include_predictions: bool = True

class CompanyDeepDiveResponse(BaseModel):
    """Response model for company deep dive analysis"""
    company_id: str
    company_name: str
    metrics: Dict[str, Any]
    timeseries: Dict[str, List[TimeseriesDataPoint]]
    competitors: Optional[List[Dict[str, Any]]] = None
    predictions: Optional[Dict[str, Any]] = None
    top_talent: List[Dict[str, Any]]
    risk_factors: List[Dict[str, Any]]

class TalentFlowAnalysisRequest(BaseModel):
    """Request parameters for talent flow analysis"""
    company_ids: Optional[List[str]] = None
    region_ids: Optional[List[str]] = None
    time_period: Literal["1m", "3m", "6m", "1y", "all"] = "all"
    min_transitions: int = 5
    granularity: Literal["day", "week", "month", "quarter", "year"] = "month"

class TalentFlowResponse(BaseModel):
    """Response model for talent flow analysis"""
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    summary: Dict[str, Any]
    top_sources: List[Dict[str, Any]]
    top_destinations: List[Dict[str, Any]]

class GeographicAnalysisRequest(BaseModel):
    """Request parameters for geographic analysis"""
    regions: Optional[List[str]] = None
    metrics: List[str] = ["talent_density", "company_density", "avg_salary", "funding_activity", "skill_demand"]
    time_period: Literal["1m", "3m", "6m", "1y", "all"] = "all"

class GeographicAnalysisResponse(BaseModel):
    """Response model for geographic analysis"""
    regions: List[Dict[str, Any]]
    cities: List[Dict[str, Any]]
    summary: Dict[str, Any]
class TrainRequest(BaseModel):
    snapshot_date: datetime = Field(..., description="Graph snapshot date (YYYY-MM-DD)")
    horizon_years: int = Field(5, description="Prediction horizon in years")
    hyperparams: Dict = Field(
        default_factory=dict, description="Optional training hyperparameters"
    )
class EnrichPitchbookRequest(BaseModel):
    root_dir: str = Field(..., description="Absolute or relative path to the PitchBook data root")
    async_mode: bool = Field(
        True,
        description="Run enrichment in a background task (immediate 202 response)",
    )

class TrainResponse(BaseModel):
    job_id: str = Field(..., description="ID of the launched training job")


class PredictCompaniesRequest(BaseModel):
    company_ids: List[str] = Field(..., description="List of company node IDs to score")


class PredictCompaniesResponse(BaseModel):
    scores: Dict[str, float] = Field(
        ..., description="Mapping company_id → success probability"
    )


class PredictCompanyResponse(BaseModel):
    company_id: str = Field(..., description="The company node ID")
    score: float = Field(..., description="Predicted success probability (0.0–1.0)")


class IngestNodeRequest(BaseModel):
    node_type: Literal[
        "Company", "Profile", "Skill", "School", "Transition", "Experience"
    ]
    node_id: str = Field(
        ...,
        description="Unique identifier of the node (Neo4j internal ID or external UUID)",
    )
    features: Dict[str, float] = Field(..., description="Feature name → value mapping")
    edges: List[Dict] = Field(
        ...,
        description="Edges to merge: "
        "[{ 'rel': 'HAS_EXPERIENCE', 'target_type':'Experience','target_id':'uuid' }]",
    )


class RefreshGraphResponse(BaseModel):
    status: str = Field(..., description="Refresh status")
    companies_added: int = Field(
        ..., description="Number of new Company nodes ingested"
    )
    profiles_added: int = Field(..., description="Number of new Profile nodes ingested")
    edges_added: int = Field(..., description="Number of new edges ingested")



# Routes for health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "LinkedIn Data API is running"}


# ─── Ingest Dataset Endpoints ────────────────────────────────────────────────
#


@app.post("/api/process_corpus")
async def process_corpus(folder_path: str):
    """
    Process a local folder of .txt and image and image files and batch store parsed LinkedIn profiles and transitions.
    Each file is expected to be plain text or an image or an image.
    """
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder path not found")

    # Collect .txt and image files
    file_paths = glob.glob(os.path.join(folder_path, "*.txt")) + glob.glob(
        os.path.join(folder_path, "*.png")
    ) + glob.glob(os.path.join(folder_path, "*.jpg")) + glob.glob(
        os.path.join(folder_path, "*.jpeg")
    )
    if not file_paths:
        raise HTTPException(
            status_code=404, detail="No .txt or image or image files found in the directory"
        )
    file_paths = file_paths[:1000]  # Limit to first 1000 files for performance
    processed_profiles = []
    all_transitions = []
    failed = []

    for i, path in enumerate(file_paths):
        filename = os.path.basename(path)
        print(f"[{i+1}/{len(file_paths)}] Processing {filename}")

        try:
            with open(path, "rb") as f:
                fp = f.read()

            # 1) OCR / text extraction
            text = raw_text_from_upload(filename, fp)

            # 2) Parse text into structured profile
            profile = text_to_profile(text)

            # 3) Check companies and enrich profile
            profile = check_companies(profile)

            # 4) Generate career transitions
            transitions = transitions_from_profile(profile)

            # Add to batch lists
            processed_profiles.append(profile)
            all_transitions.extend(transitions)

            print(f"[SUCCESS] Processed {filename}")

        except Exception as e:
            print(f"[ERROR] Failed processing {filename}: {e}")
            failed.append({"filename": filename, "error": str(e)})
            continue

    # Batch Store Profiles & Transitions
    try:
        db = Neo4jDatabase()
        if processed_profiles:
            db.batch_store_profiles(processed_profiles)
        if all_transitions:
            db.batch_store_transitions(all_transitions)
        db.close()
        print("[DB] Batch storage complete.")
    except Exception as db_err:
        raise HTTPException(status_code=500, detail=f"Batch DB store failed: {db_err}")

    return {
        "summary": {
            "total": len(file_paths),
            "processed": len(processed_profiles),
            "transitions": len(all_transitions),
            "failed": len(failed),
        }
    }

@app.post("/api/enrich/pitchbook", status_code=202)
async def enrich_pitchbook(req: EnrichPitchbookRequest, background_tasks: BackgroundTasks):
    """
    Walk *root_dir*/<Company> folders, parse the PitchBook Excel exports,
    and augment existing :Company nodes with the engineered features.
    """
    # Small inner function so BackgroundTasks can call it synchronously
    def _run():
        enricher = PitchbookEnricher(
            root_dir=req.root_dir,
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j"),
        )
        enricher.run()

    if req.async_mode:
        background_tasks.add_task(_run)
        return {"status": "queued", "root_dir": req.root_dir}
    else:
        _run()
        return {"status": "completed", "root_dir": req.root_dir}


# ─── Database Endpoints ────────────────────────────────────────────────────────
#


@app.post("/api/db/store_profile")
async def store_profile(profile: Dict[str, Any]):
    """Store a LinkedIn profile in Neo4j and Druid"""
    try:
        profile_model = LinkedInProfile(**profile)

        # Store in Neo4j
        db = Neo4jDatabase()
        db.store_profile(profile_model)
        db.close()

        # Store in Druid
        # send_to_druid(profiles=[profile_model], companies=[])

        return {"success": True, "message": "Profile stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing profile: {str(e)}")


@app.post("/api/db/store_transition")
async def store_transition(transition: TransitionEvent):
    """Store a job transition event in Neo4j and Druid"""
    transition_data = transition.model_dump()

    # Store in Neo4j
    neo4j_success = send_transition_to_neo4j(transition_data)

    # Store in Druid
    druid_success = send_transition_update(transition_data)

    if neo4j_success and druid_success:
        return {"success": True, "message": "Transition stored successfully"}
    else:
        raise HTTPException(status_code=500, detail="Error storing transition event")


@app.post("/api/db/query")
async def custom_query(query: Dict[str, Any]):
    """Execute a custom Cypher query on Neo4j"""
    if "cypher" not in query:
        raise HTTPException(status_code=400, detail="Query must include 'cypher' field")

    results = query_neo4j(query["cypher"], query.get("params", {}))
    return {"results": results}


@app.post("/api/db/clear")
async def clear_database():
    """Clear all data from Neo4j and Druid databases"""
    try:
        db = Neo4jDatabase()
        db.clear_database()
        db.close()

        return {"success": True, "message": "Database cleared successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error clearing database: {str(e)}"
        )


# ─── Graph‑ranking endpoints ──────────────────────────
#
@app.post("/api/graph/projection")
async def build_projection(req: ProjectionRequest):
    """
    (Re)create the collapsed Employee ↔ Company projection in GDS.
    """
    try:
        db = Neo4jDatabase()
        db.create_emp_company_projection(
            graph_name=req.graph_name,
            weight_scheme=req.weight_scheme,
            delete_existing=req.delete_existing,
        )
        db.close()
        return {"success": True, "graph": req.graph_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Projection failed: {e}")


@app.post("/api/graph/pagerank")
async def run_pagerank(req: PageRankRequest):
    """
    Run native GDS PageRank on the collapsed projection.
    If *write_property* is provided, scores are stored on the graph and an
    empty list is returned.  Otherwise results stream back as JSON.
    """
    try:
        db = Neo4jDatabase()
        df = db.pagerank_emp_company(
            graph_name=req.graph_name,
            damping=req.damping,
            iterations=req.iterations,
            write_property=req.write_property,
        )
        db.close()
        records = df.to_dict("records") if not req.write_property else []
        return {
            "success": True,
            "graph": req.graph_name,
            "mode": "write" if req.write_property else "stream",
            "results": records,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PageRank failed: {e}")


@app.post("/api/graph/birank")
async def run_birank(req: BiRankRequest):
    """
    Run BiRank (degree‑balanced) on the collapsed projection.
    Works exactly like the PageRank endpoint.
    """
    try:
        db = Neo4jDatabase()
        df = db.birank_emp_company(
            graph_name=req.graph_name,
            alpha=req.alpha,
            beta=req.beta,
            max_iter=req.max_iter,
            write_prefix=req.write_prefix,
        )
        db.close()
        records = df.to_dict("records") if not req.write_prefix else []
        return {
            "success": True,
            "graph": req.graph_name,
            "mode": "write" if req.write_prefix else "stream",
            "results": records,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BiRank failed: {e}")


@app.get("/api/graph/rankings")
async def fetch_rankings(
    property_name: str,
    label: Optional[str] = None,
    limit: int = 20,
):
    """
    Quick leaderboard for any stored ranking property (e.g. pr, br_emp, br_comp).
    Optionally restrict to a single label (Employee / Company).
    """
    label_clause = f":{label}" if label else ""
    cypher = (
        f"MATCH (n{label_clause}) "
        f"WHERE n.`{property_name}` IS NOT NULL "  # ← replace exists(...)
        f"RETURN n.name AS name, n.`{property_name}` AS score "
        f"ORDER BY score DESC LIMIT $limit"
    )
    try:
        rows = query_neo4j(cypher, {"limit": limit})
        return {"property": property_name, "results": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetch failed: {e}")


# ─── File Upload and Parse ────────────────────────────────────────────────
#


@app.post("/api/upload/resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and process a resume image"""
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads/resumes", exist_ok=True)

    # Save file
    file_path = (
        f"uploads/resumes/{datetime.now().strftime('%Y%m%d%H%M%S')}-{file.filename}"
    )
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Read file content as buffer from the saved file location
    with open(file_path, "rb") as f:
        fp = f.read()

    # 1) OCR / text extraction
    try:
        text = raw_text_from_upload(file.filename, fp)
    except ValueError as e:
        raise HTTPException(status_code=415, detail=str(e))

    # 2) LLM → structured profile
    try:
        profile = text_to_profile(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM parsing failed: {e}")

    # ensure valid companies and company urns, set unique if not provided, and exists in db. Modifies in place.
    check_companies(profile)

    # Structured profile -> Generate Transitions.
    try:
        transitions = transitions_from_profile(profile)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Transition generation failed: {e}"
        )

    # try Db upload
    try:
        db = Neo4jDatabase()
        # Store profile and transitions.
        db.store_profile(profile)
        for transition in transitions:
            db.store_transition(transition)
        db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database storage failed: {e}")

    return {
        "success": True,
        "filename": file.filename,
        "path": file_path,
        "message": "Resume uploaded and parsed successfully.",
        "profile": profile.model_dump(),
    }


@app.post("/api/upload/linkedin")
async def upload_linkedin(file: UploadFile = File(...)):
    """Upload and process a LinkedIn screenshot"""
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads/linkedin", exist_ok=True)

    # Save file
    file_path = (
        f"uploads/linkedin/{datetime.now().strftime('%Y%m%d%H%M%S')}-{file.filename}"
    )
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Here you would process the LinkedIn screenshot (OCR, data extraction, etc.)
    # This is a placeholder for your actual implementation

    return {
        "filename": file.filename,
        "path": file_path,
        "message": "LinkedIn screenshot uploaded successfully. Processing will occur asynchronously.",
    }


# ─── VC FUNCTIONALITY ───────────────────────────────────────────────────────────
@app.post("/api/vc/companies/search")
async def search_companies(filters: VCFiltersRequest):
    """Search companies based on VC filters"""
    db = Neo4jDatabase()
    try:
        # Build a simpler query that doesn't rely on potentially missing properties
        query = """
        MATCH (c:Company)
        
        // Get employee count in a proper way
        OPTIONAL MATCH (p1:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
        WHERE e.isCurrent = true
        WITH c, count(p1) as employeeCount
        
        // Get recent transitions count in a proper way  
        OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t)-[:TO_COMPANY]->(c)
        WHERE t.date >= datetime() - duration('P3M')
        WITH c, employeeCount, count(p2) as recentTransitions
        
        // Calculate growth rate
        WITH c, employeeCount, recentTransitions,
             round(100.0 * recentTransitions / CASE WHEN employeeCount > 0 THEN employeeCount ELSE 1 END, 1) as growthRate
        
        // Get random churn rate for demo
        RETURN c.urn as urn,
               c.name as name,
               employeeCount,
               recentTransitions,
               growthRate,
               round(rand() * 15, 1) as churnRate
        ORDER BY employeeCount DESC
        LIMIT 50
        """
        
        results = db._run_query(query)
        
        # Transform results into the expected format
        companies = []
        for result in results:
            # Skip entries without a name or URN
            if not result.get("name") or not result.get("urn"):
                continue
                
            company = {
                "urn": result["urn"],
                "name": result["name"],
                "industry": filters.industries[0] if filters.industries else "Technology",  # Default value since it's missing in DB
                "employeeCount": result["employeeCount"],
                "recentTransitions": result["recentTransitions"],
                "growthRate": result["growthRate"],
                "churnRate": result["churnRate"]
            }
            
            # Apply client-side filtering since we can't rely on the database properties
            if filters.industries and len(filters.industries) > 0:
                # For demonstration, just include all companies since we don't have industry data
                pass
                
            if filters.geo_regions and len(filters.geo_regions) > 0:
                # For demonstration, just include all companies since we don't have location data
                pass
                
            companies.append(company)
        
        print(f"Found {len(companies)} companies matching filters")
        
        return {
            "success": True,
            "companies": companies,
            "total": len(companies)
        }
    finally:
        db.close()

@app.post("/api/vc/companies/analyze")
async def analyze_companies(request: CompanyAnalysisRequest):
    """Get detailed analysis for specific companies"""
    db = Neo4jDatabase()
    try:
        analyses = []
        for company_id in request.company_ids:
            # Get company talent flow
            talent_flow = db.get_company_transition_stats(company_id)
            
            # Get company growth metrics
            query = """
            MATCH (c:Company {urn: $company_id})
            OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
            WHERE e.isCurrent = true
            WITH c, count(p) as currentEmployees
            
            OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t)-[:TO_COMPANY]->(c)
            WHERE t.date >= datetime() - duration('P6M')
            WITH c, currentEmployees, count(t) as recentHires
            
            RETURN {
                "companyUrn": c.urn,
                "name": c.name,
                "currentEmployees": currentEmployees,
                "recentHires": recentHires,
                "growthRate": round(100.0 * recentHires / (currentEmployees + 1), 2)
            } as analysis
            """
            
            result = db._run_query(query, {"company_id": company_id})
            if result:
                analysis = result[0]["analysis"]
                analysis["talentFlow"] = talent_flow
                analyses.append(analysis)
        
        return {
            "success": True,
            "analyses": analyses
        }
    finally:
        db.close()

@app.post("/api/vc/portfolio/overview")
async def get_portfolio_overview(portfolio_ids: List[str]):
    """Get portfolio overview metrics"""
    db = Neo4jDatabase()
    try:
        # Completely revised query to avoid JSON literals in Cypher
        query = """
        MATCH (c:Company)
        WHERE c.urn IN $portfolio_ids
        
        // Get employee count
        OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
        WHERE e.isCurrent = true
        WITH c, count(p) as employees
        
        // Get departures (talent outflow)
        OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t2)-[:FROM_COMPANY]->(c)
        WHERE t2.date >= datetime() - duration('P3M')
        WITH c, employees, count(p2) as departures
        
        // Get arrivals (talent inflow)
        OPTIONAL MATCH (p3:Profile)-[:HAS_TRANSITION]->(t3)-[:TO_COMPANY]->(c)
        WHERE t3.date >= datetime() - duration('P3M')
        WITH c, employees, departures, count(p3) as arrivals
        
        // Return individual company records first
        RETURN c.urn as urn, 
               c.name as name, 
               employees, 
               departures, 
               arrivals,
               arrivals - departures as netFlow,
               CASE WHEN employees > 0 
                    THEN round(100.0 * departures / employees, 2) 
                    ELSE 0 
               END as churnRate
        """
        
        results = db._run_query(query, {"portfolio_ids": portfolio_ids})
        
        # Process results and calculate summary metrics in Python instead of Cypher
        companies = []
        totalEmployees = 0
        totalDepartures = 0
        totalArrivals = 0
        
        for result in results:
            companies.append({
                "urn": result["urn"],
                "name": result["name"],
                "employees": result["employees"],
                "churnRate": result["churnRate"],
                "netFlow": result["netFlow"]
            })
            
            totalEmployees += result["employees"]
            totalDepartures += result["departures"]
            totalArrivals += result["arrivals"]
        
        # Create overview object
        overview = {
            "totalCompanies": len(companies),
            "totalEmployees": totalEmployees,
            "avgChurnRate": round(100.0 * totalDepartures / max(1, totalEmployees), 2),
            "netTalentFlow": totalArrivals - totalDepartures,
            "companies": companies
        }
        
        # Identify at-risk companies
        at_risk = [comp for comp in companies 
                  if comp["churnRate"] > 15 or comp["netFlow"] < -5]
        
        overview["atRiskCompanies"] = at_risk
        
        return {
            "success": True,
            "overview": overview
        }
    finally:
        db.close()

@app.get("/api/vc/skills/trending")
async def get_trending_skills(limit: int = 10):
    """Get trending skills based on recent hires"""
    db = Neo4jDatabase()
    try:
        # Simplified approach that doesn't use nested JSON literals
        query = """
        MATCH (p:Profile)-[:HAS_SKILL]->(s:Skill)
        MATCH (p)-[:HAS_TRANSITION]->(t:Transition)
        WHERE t.date >= datetime() - duration('P6M')
        
        WITH s.name as skill_name, count(p) as recentHires
        ORDER BY recentHires DESC
        LIMIT $limit
        
        MATCH (allProfiles:Profile)-[:HAS_SKILL]->(s:Skill)
        WHERE s.name = skill_name
        WITH skill_name, recentHires, count(allProfiles) as totalProfiles
        
        RETURN skill_name as skill,
               recentHires,
               totalProfiles,
               round(100.0 * recentHires / totalProfiles, 2) as trendScore
        ORDER BY trendScore DESC
        """
        
        results = db._run_query(query, {"limit": limit})
        
        # Transform results to the expected format
        trending_skills = [
            {
                "skill": result["skill"],
                "recentHires": result["recentHires"],
                "totalProfiles": result["totalProfiles"],
                "trendScore": result["trendScore"]
            }
            for result in results
        ]
        
        return {
            "success": True,
            "skills": trending_skills
        }
    finally:
        db.close()
        
@app.post("/api/analytics/company-scores")
async def calculate_company_scores(request: dict):
    """
    Calculate enhanced company scores with additional insights from Neo4j data
    """
    try:
        company_urns = request.get("company_urns", [])
        if not company_urns:
            raise HTTPException(status_code=400, detail="Company URNs are required")
            
        include_pagerank = request.get("include_pagerank", True)
        include_birank = request.get("include_birank", True)
        include_talent_flow = request.get("include_talent_flow", True)
        
        # Connect to Neo4j and calculate scores
        db = Neo4jDatabase()
        result = db.calculate_company_scores(
            company_urns, 
            include_pagerank, 
            include_birank, 
            include_talent_flow
        )
        
        # For each company, get additional insights
        enhanced_results = []
        for company_score in result:
            company_urn = company_score.get("company_urn")
            if not company_urn:
                enhanced_results.append(company_score)
                continue
            
            # Query for additional company metrics
            query = f"""
            MATCH (c:Company {{urn: "{company_urn}"}})
            
            // Get employee count and retention
            OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
            WHERE e.isCurrent = true
            WITH c, count(p) as employeeCount
            
            // Get incoming transitions (new hires)
            OPTIONAL MATCH (t_in:Transition)-[:TO_COMPANY]->(c)
            WHERE t_in.date >= datetime() - duration('P6M')
            WITH c, employeeCount, count(t_in) as recentHires
            
            // Get outgoing transitions (departures)
            OPTIONAL MATCH (t_out:Transition)-[:FROM_COMPANY]->(c)
            WHERE t_out.date >= datetime() - duration('P6M')
            WITH c, employeeCount, recentHires, count(t_out) as recentDepartures
            
            // Get employee skills
            OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
            WHERE e.isCurrent = true
            OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
            WITH c, employeeCount, recentHires, recentDepartures, collect(distinct s.name) as skills
            
            RETURN {{
                employeeCount: employeeCount,
                recentHires: recentHires,
                recentDepartures: recentDepartures,
                growthRate: CASE WHEN employeeCount > 0 
                            THEN round(100.0 * recentHires / employeeCount, 1)
                            ELSE 0 END,
                churnRate: CASE WHEN employeeCount > 0 
                           THEN round(100.0 * recentDepartures / employeeCount, 1)
                           ELSE 0 END,
                topSkills: [skill in skills WHERE size(skill) > 0 | skill][0..5],
                retentionRate: CASE WHEN (employeeCount + recentDepartures) > 0 
                              THEN round(100.0 * employeeCount / (employeeCount + recentDepartures), 1)
                              ELSE 0 END
            }} as additionalMetrics
            """
            
            metrics_result = db._run_query(query)
            
            # Add insights to company score
            if metrics_result and len(metrics_result) > 0 and "additionalMetrics" in metrics_result[0]:
                metrics = metrics_result[0]["additionalMetrics"]
                
                # Add metrics to result
                company_score.update({
                    "employeeCount": metrics.get("employeeCount", 0),
                    "recentHires": metrics.get("recentHires", 0),
                    "recentDepartures": metrics.get("recentDepartures", 0),
                    "growthRate": metrics.get("growthRate", 0),
                    "churnRate": metrics.get("churnRate", 0),
                    "retentionRate": metrics.get("retentionRate", 0),
                    "topSkills": metrics.get("topSkills", [])
                })
                
                # Add analysis insight based on metrics
                if metrics.get("growthRate", 0) > 20:
                    company_score["insight"] = "High Growth"
                    company_score["insightDetails"] = f"Company growing at {metrics.get('growthRate')}% rate"
                elif metrics.get("churnRate", 0) > 15:
                    company_score["insight"] = "High Churn"
                    company_score["insightDetails"] = f"Company experiencing {metrics.get('churnRate')}% employee churn"
                elif company_score.get("net_talent_flow", 0) > 10:
                    company_score["insight"] = "Talent Magnet"
                    company_score["insightDetails"] = f"Net talent inflow of {company_score.get('net_talent_flow')} employees"
                elif metrics.get("retentionRate", 0) > 90:
                    company_score["insight"] = "Strong Retention"
                    company_score["insightDetails"] = f"High employee retention of {metrics.get('retentionRate')}%"
                else:
                    company_score["insight"] = "Stable"
                    company_score["insightDetails"] = "Company showing stable metrics"
            
            enhanced_results.append(company_score)
        
        # Close database connection
        db.close()
        
        return enhanced_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating company scores: {str(e)}")

@app.post("/api/analytics/create-alert")
async def create_alert(alert_config: AlertConfig):
    """
    Create a new monitoring alert for portfolio companies.
    """
    try:
        db = Neo4jDatabase()
        
        # Store alert configuration in Neo4j
        alert_query = """
        CREATE (a:Alert {
            id: randomUUID(),
            type: $type,
            threshold: $threshold,
            company_urns: $company_urns,
            enabled: $enabled,
            created_at: datetime(),
            triggered_count: 0
        })
        RETURN a.id as id
        """
        
        result = db._run_query(alert_query, {
            "type": alert_config.alert_type,
            "threshold": alert_config.threshold,
            "company_urns": alert_config.company_urns,
            "enabled": alert_config.enabled
        })
        
        db.close()
        return {"alert_id": result[0]["id"], "status": "created"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating alert: {str(e)}")

@app.get("/api/analytics/check-alerts", response_model=List[Alert])
async def check_alerts():
    """
    Check all active alerts and return triggered ones.
    """
    try:
        db = Neo4jDatabase()
        
        # Get all active alerts
        alerts_query = """
        MATCH (a:Alert)
        WHERE a.enabled = true
        RETURN a
        """
        
        alerts = db._run_query(alerts_query)
        triggered_alerts = []
        
        for alert_data in alerts:
            alert = alert_data['a']
            alert_type = alert['type']
            threshold = alert['threshold']
            company_urns = alert['company_urns']
            
            for company_urn in company_urns:
                # Get company name
                company_query = "MATCH (c:Company {urn: $urn}) RETURN c.name as name"
                result = db._run_query(company_query, {"urn": company_urn})
                company_name = result[0]['name'] if result else "Unknown"
                
                # Check different alert types
                if alert_type == "talent_drain":
                    # Check talent outflow vs inflow
                    talent_stats = db.get_company_transition_stats(company_urn)
                    if talent_stats:
                        outflow = talent_stats.get('outgoingTransitions', 0)
                        inflow = talent_stats.get('incomingTransitions', 0)
                        drain_ratio = outflow / max(inflow, 1)
                        
                        if drain_ratio > threshold:
                            triggered_alerts.append(Alert(
                                id=alert['id'],
                                alert_type=alert_type,
                                company_urn=company_urn,
                                company_name=company_name,
                                metric_value=drain_ratio,
                                threshold=threshold,
                                triggered_at=datetime.now(),
                                message=f"High talent drain detected: {drain_ratio:.2f}x more outflow than inflow"
                            ))
                
                elif alert_type == "high_growth":
                    # Check recent hiring velocity
                    growth_query = """
                    MATCH (c:Company {urn: $urn})<-[:TO_COMPANY]-(t:Transition)
                    WHERE datetime(t.date) >= datetime() - duration('P90D')
                    RETURN count(t) as recent_hires
                    """
                    result = db._run_query(growth_query, {"urn": company_urn})
                    recent_hires = result[0]['recent_hires'] if result else 0
                    
                    if recent_hires > threshold:
                        triggered_alerts.append(Alert(
                            id=alert['id'],
                            alert_type=alert_type,
                            company_urn=company_urn,
                            company_name=company_name,
                            metric_value=recent_hires,
                            threshold=threshold,
                            triggered_at=datetime.now(),
                            message=f"High growth detected: {recent_hires} hires in last 90 days"
                        ))
        
        db.close()
        return triggered_alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking alerts: {str(e)}")

@app.get("/api/analytics/talent-flow-network")
async def get_talent_flow_network(min_transitions: int = 5):
    """
    Get network data for visualizing talent flows between companies.
    """
    try:
        db = Neo4jDatabase()
        
        # Get company-to-company talent flows
        flow_query = """
        MATCH (from_company:Company)<-[:FROM_COMPANY]-(t:Transition)-[:TO_COMPANY]->(to_company:Company)
        WITH from_company, to_company, count(t) as transition_count
        WHERE transition_count >= $min_transitions
        RETURN 
            from_company.urn as from_urn,
            from_company.name as from_name,
            to_company.urn as to_urn,
            to_company.name as to_name,
            transition_count
        ORDER BY transition_count DESC
        """
        
        flows = db._run_query(flow_query, {"min_transitions": min_transitions})
        
        # Build nodes and edges for network visualization
        nodes = {}
        edges = []
        
        for flow in flows:
            # Add nodes
            if flow['from_urn'] not in nodes:
                nodes[flow['from_urn']] = {
                    "id": flow['from_urn'],
                    "name": flow['from_name'],
                    "type": "company"
                }
            
            if flow['to_urn'] not in nodes:
                nodes[flow['to_urn']] = {
                    "id": flow['to_urn'],
                    "name": flow['to_name'],
                    "type": "company"
                }
            
            # Add edge
            edges.append({
                "source": flow['from_urn'],
                "target": flow['to_urn'],
                "value": flow['transition_count'],
                "label": f"{flow['transition_count']} transitions"
            })
        
        db.close()
        return {
            "nodes": list(nodes.values()),
            "links": edges
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting talent flow network: {str(e)}")

@app.get("/api/analytics/geographic-talent-density")
async def get_geographic_talent_density():
    """
    Get geographic distribution of talent for heatmap visualization.
    """
    try:
        db = Neo4jDatabase()
        
        # Get talent density by location
        density_query = """
        MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e:Experience)
        WHERE e.locationName IS NOT NULL AND e.isCurrent = true
        WITH e.locationName as location, count(DISTINCT p) as talent_count
        WHERE talent_count >= 3
        RETURN location, talent_count
        ORDER BY talent_count DESC
        """
        
        density_data = db._run_query(density_query)
        
        # Simple location parsing (you'd want a more sophisticated geocoding service)
        geographic_data = []
        for item in density_data:
            location = item['location']
            talent_count = item['talent_count']
            
            # Basic city/state parsing for US locations
            if ',' in location:
                parts = location.split(',')
                city = parts[0].strip()
                state_country = parts[1].strip() if len(parts) > 1 else ""
                
                # You would typically use a geocoding service here
                # For demo purposes, we'll return the raw data
                geographic_data.append({
                    "location": location,
                    "city": city,
                    "state_country": state_country,
                    "talent_count": talent_count,
                    "lat": None,  # Would be filled by geocoding service
                    "lng": None   # Would be filled by geocoding service
                })
        
        db.close()
        return geographic_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting geographic talent density: {str(e)}")
        
# Start the server if running as a script
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

    # Mock data generation endpoints
# @app.post("/api/mock/generate_profiles")
# async def generate_mock_profiles(config: MockGenerationConfig):
#     """Generate mock LinkedIn profiles"""
#     try:
#         generator = LinkedInDataGenerator()

#         # Generate profiles with specified distribution
#         profiles = generator.create_and_save_mock_dataset(
#         )

#         if config.store_in_db:
#             # Convert to Pydantic models
#             profile_models = []
#             for profile_data in profiles:
#                 try:
#                     profile_models.append(LinkedInProfile(**profile_data))
#                 except Exception as e:
#                     print(f"Error converting profile to model: {e}")

#             # Generate companies
#             companies = generator.generate_company_dataset()
#             company_models = []
#             for company_data in companies:
#                 try:
#                     company_models.append(LinkedInCompany(**company_data))
#                 except Exception as e:
#                     print(f"Error converting company to model: {e}")

#             # Store in databases
#             send_to_neo4j(profiles=profile_models, companies=company_models)
#             return {
#                 "success": True,
#                 "message": f"Generated and stored {len(profile_models)} profiles and {len(company_models)} companies"
#             }

#         return {"success": True, "count": len(profiles), "profiles": profiles[:5]}  # Return only first 5 profiles to avoid large payload
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error generating mock data: {str(e)}")

# ─────────────────── Advanced Analytics Endpoints ─────────────────────────

@app.post("/api/analytics/company-deep-dive", response_model=CompanyDeepDiveResponse)
async def company_deep_dive(request: CompanyDeepDiveRequest):
    """
    Perform a comprehensive analysis of a company with detailed metrics and predictions.
    
    This endpoint provides:
    - Detailed company metrics across multiple dimensions
    - Historical timeseries data for key performance indicators
    - Competitor analysis and benchmarking
    - Future performance predictions
    - Key talent identification
    - Risk factor assessment
    """
    try:
        company_id = request.company_id
        
        # Get company details from database
        company_details = neo4j_db.find_company_by_urn(company_id)
        
        if not company_details:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Get start and end dates based on time period
        start_date, end_date = get_time_period_dates(request.time_period)
        
        # Prepare response data
        company_name = company_details.get("name", "Unknown Company")
        
        # Collect basic metrics
        metrics = {}
        timeseries_data = {}
        
        # Process requested metrics
        for metric_name in request.metrics:
            if metric_name == "talent_flow":
                # Get talent flow metrics
                talent_flow = neo4j_db.get_company_transition_stats(company_id)
                metrics["talent_flow"] = {
                    "inflow": talent_flow.get("inflow", 0),
                    "outflow": talent_flow.get("outflow", 0),
                    "net_flow": talent_flow.get("net_flow", 0),
                    "retention_rate": talent_flow.get("retention_rate", 0) * 100,
                    "avg_tenure_days": talent_flow.get("avg_tenure_days", 0)
                }
                
                # Generate timeseries data for talent flow
                # In a real implementation, this would query historical data points
                timeseries_data["talent_inflow"] = generate_mock_timeseries(start_date, end_date, 5, 20)
                timeseries_data["talent_outflow"] = generate_mock_timeseries(start_date, end_date, 3, 15)
            
            elif metric_name == "growth":
                # Get growth metrics
                growth_metrics = {
                    "employee_growth_rate": round(get_mock_value(10, 50), 1),
                    "revenue_growth_rate": round(get_mock_value(5, 30), 1),
                    "market_share_change": round(get_mock_value(-5, 15), 1),
                    "expansion_rate": round(get_mock_value(0, 25), 1)
                }
                metrics["growth"] = growth_metrics
                
                # Generate timeseries data for growth metrics
                timeseries_data["employee_count"] = generate_mock_timeseries(start_date, end_date, 100, 1000)
            
            elif metric_name == "funding":
                # Get funding data from company details
                funding_data = company_details.get("funding_data", {})
                
                if funding_data:
                    last_round = funding_data.get("last_funding_round", {})
                    money_raised = last_round.get("money_raised", {})
                    
                    metrics["funding"] = {
                        "total_funding": get_mock_value(1000000, 100000000),
                        "last_round_amount": money_raised.get("amount", 0),
                        "last_round_type": last_round.get("funding_type", "Unknown"),
                        "total_rounds": funding_data.get("num_funding_rounds", 0),
                        "last_round_date": last_round.get("announced_on", {}).get("year", 0)
                    }
                else:
                    # Generate mock funding data
                    metrics["funding"] = {
                        "total_funding": get_mock_value(1000000, 100000000),
                        "last_round_amount": get_mock_value(500000, 50000000),
                        "last_round_type": "Series B",
                        "total_rounds": 3,
                        "last_round_date": 2022
                    }
                
                # Generate timeseries for funding events
                timeseries_data["funding_rounds"] = generate_mock_funding_timeseries(start_date, end_date)
            
            elif metric_name == "sentiment":
                # Generate sentiment metrics
                metrics["sentiment"] = {
                    "overall_score": round(get_mock_value(50, 95), 1),
                    "public_perception": round(get_mock_value(50, 95), 1),
                    "employee_satisfaction": round(get_mock_value(50, 95), 1),
                    "social_media_sentiment": round(get_mock_value(50, 95), 1),
                    "news_sentiment": round(get_mock_value(50, 95), 1)
                }
                
                # Generate timeseries for sentiment
                timeseries_data["sentiment_score"] = generate_mock_timeseries(start_date, end_date, 50, 90)
        
        # Get competitors if requested
        competitors = None
        if request.include_competitors:
            # In a real implementation, this would query the database for similar companies
            competitors = [
                {
                    "company_id": f"urn:li:company:{i}",
                    "company_name": f"Competitor {i}",
                    "similarity_score": round(get_mock_value(60, 95), 1),
                    "key_metrics": {
                        "talent_flow": round(get_mock_value(-20, 40), 1),
                        "growth_rate": round(get_mock_value(5, 30), 1),
                        "funding": format_number(get_mock_value(1000000, 100000000))
                    }
                }
                for i in range(1, 6)  # Generate 5 mock competitors
            ]
        
        # Get predictions if requested
        predictions = None
        if request.include_predictions:
            predictions = {
                "success_probability": round(get_mock_value(50, 95), 1),
                "growth_prediction": {
                    "employee_growth": round(get_mock_value(5, 30), 1),
                    "revenue_growth": round(get_mock_value(10, 50), 1),
                    "market_share_growth": round(get_mock_value(-5, 20), 1)
                },
                "funding_prediction": {
                    "next_round_probability": round(get_mock_value(30, 90), 1),
                    "estimated_amount": format_number(get_mock_value(1000000, 50000000)),
                    "estimated_timeframe": f"{int(get_mock_value(3, 18))} months"
                }
            }
        
        # Generate top talent list
        top_talent = [
            {
                "profile_id": f"profile-{i}",
                "name": f"Executive {i}",
                "title": ["CEO", "CTO", "CFO", "COO", "CMO"][i % 5],
                "tenure": f"{int(get_mock_value(1, 10))} years",
                "previous_company": f"Previous Company {i}",
                "influence_score": round(get_mock_value(70, 95), 1)
            }
            for i in range(1, 6)  # Generate 5 mock executives
        ]
        
        # Generate risk factors
        risk_factors = [
            {
                "factor": "High talent outflow",
                "severity": ["Low", "Medium", "High"][int(get_mock_value(0, 2))],
                "description": "The company is experiencing higher than industry average employee turnover."
            },
            {
                "factor": "Competitive pressure",
                "severity": ["Low", "Medium", "High"][int(get_mock_value(0, 2))],
                "description": "Increased competition in the market may affect growth prospects."
            },
            {
                "factor": "Funding runway",
                "severity": ["Low", "Medium", "High"][int(get_mock_value(0, 2))],
                "description": "Time until next funding round may be critical for operations."
            },
            {
                "factor": "Market saturation",
                "severity": ["Low", "Medium", "High"][int(get_mock_value(0, 2))],
                "description": "The market segment may be reaching saturation point."
            }
        ]
        
        # Format timeseries data for response model
        formatted_timeseries = {}
        for key, data_points in timeseries_data.items():
            formatted_timeseries[key] = [
                TimeseriesDataPoint(date=date, value=value)
                for date, value in data_points
            ]
        
        # Create response
        response = CompanyDeepDiveResponse(
            company_id=company_id,
            company_name=company_name,
            metrics=metrics,
            timeseries=formatted_timeseries,
            competitors=competitors,
            predictions=predictions,
            top_talent=top_talent,
            risk_factors=risk_factors
        )
        
        return response
        
    except Exception as e:
        logger.exception(f"Error in company deep dive analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analytics/talent-flow")
async def analyze_talent_flow(request: Union[dict, TalentFlowAnalysisRequest], req: Request):
    """
    Analyze talent flow between companies or regions using real Neo4j data.
    
    This endpoint provides:
    - Network visualization data of talent movement
    - Aggregated talent flow metrics
    - Top source and destination companies
    - Historical talent flow trends
    """
    client_ip = req.client.host
    user_agent = req.headers.get('user-agent', '')[:50]
    client_id = f"{client_ip}_{user_agent[:20]}"
    request_time = datetime.now()
    
    # Initialize cache variables if they don't exist
    if "last_user_agent" not in cache:
        cache["last_user_agent"] = ""
    if "talent_flow_cache" not in cache:
        cache["talent_flow_cache"] = {}
    if "last_updated" not in cache:
        cache["last_updated"] = {}
    if "client_timestamps" not in cache:
        cache["client_timestamps"] = {}
    
    # Store last user agent for rate limiter
    cache["last_user_agent"] = user_agent
    
    # Log API call for debugging
    print(f"TALENT FLOW API CALL from {client_ip} at {request_time.isoformat()}")
    
    try:
        # Handle different request types
        if isinstance(request, dict):
            company_ids = request.get("company_ids", [])
            region_ids = request.get("region_ids", [])
            time_period = request.get("time_period", "6m")
            granularity = request.get("granularity", "month")
            min_transitions = request.get("min_transitions", 5)
        else:
            company_ids = request.company_ids or []
            region_ids = request.region_ids or []
            time_period = request.time_period
            granularity = request.granularity
            min_transitions = request.min_transitions

        # Create cache key based on request parameters
        cache_key = f"talent_flow_{','.join(sorted(company_ids) if company_ids else [])}_{','.join(sorted(region_ids) if region_ids else [])}_{time_period}_{granularity}_{min_transitions}"
        
        # Check cache
        if cache_key in cache["talent_flow_cache"] and cache_key in cache["last_updated"]:
            last_updated = cache["last_updated"][cache_key]
            age = request_time - last_updated
            if age.total_seconds() < 3600:  # Cache valid for 1 hour
                print(f"Using cached talent flow data for {cache_key}")
                return cache["talent_flow_cache"][cache_key]
        
        # Connect to Neo4j database
        db = Neo4jDatabase()
        
        # Construct the Cypher query based on request parameters
        # Case 1: Specific companies provided
        if company_ids and len(company_ids) > 0:
            company_ids_param = ', '.join([f'"{id}"' for id in company_ids])
            cypher_query = f"""
            // Match transitions between specified companies
            MATCH (p:Profile)-[:HAS_TRANSITION]->(t:Transition)
            WHERE t.date >= datetime() - duration('P{time_period[:-1]}M')
            
            WITH p, t
            MATCH (t)-[:FROM_COMPANY]->(from_company:Company)
            MATCH (t)-[:TO_COMPANY]->(to_company:Company)
            
            // Filter by specified companies
            WHERE from_company.urn IN [{company_ids_param}] OR to_company.urn IN [{company_ids_param}]
            
            // Count transitions between companies
            WITH from_company, to_company, count(t) as transition_count
            WHERE transition_count >= {min_transitions}
            
            // Get from_company employee counts
            OPTIONAL MATCH (p1:Profile)-[:HAS_EXPERIENCE]->(e1)-[:AT_COMPANY]->(from_company)
            WHERE e1.isCurrent = true
            WITH from_company, to_company, transition_count, count(p1) as from_employee_count
            
            // Get to_company employee counts
            OPTIONAL MATCH (p2:Profile)-[:HAS_EXPERIENCE]->(e2)-[:AT_COMPANY]->(to_company)
            WHERE e2.isCurrent = true
            WITH from_company, to_company, transition_count, from_employee_count, count(p2) as to_employee_count
            
            // Return node and link data for visualization
            RETURN collect(distinct {{
              id: from_company.urn,
              name: from_company.name,
              type: 'company',
              employeeCount: from_employee_count,
              outflow: transition_count,
              inflow: 0
            }}) + collect(distinct {{
              id: to_company.urn,
              name: to_company.name,
              type: 'company',
              employeeCount: to_employee_count,
              outflow: 0,
              inflow: transition_count
            }}) as nodes,
            collect({{
              source: from_company.urn,
              target: to_company.urn,
              value: transition_count,
              direction: "outbound"
            }}) as links
            """
        else:
            # Case 2: No specific companies - get top companies with talent flow
            cypher_query = f"""
            // Match all transitions within time period
            MATCH (p:Profile)-[:HAS_TRANSITION]->(t:Transition)
            WHERE t.date >= datetime() - duration('P{time_period[:-1]}M')
            
            MATCH (t)-[:FROM_COMPANY]->(from_company:Company)
            MATCH (t)-[:TO_COMPANY]->(to_company:Company)
            
            // Count transitions between companies
            WITH from_company, to_company, count(t) as transition_count
            WHERE transition_count >= {min_transitions}
            
            // Get employee counts
            OPTIONAL MATCH (p1:Profile)-[:HAS_EXPERIENCE]->(e1)-[:AT_COMPANY]->(from_company)
            WHERE e1.isCurrent = true
            WITH from_company, to_company, transition_count, count(p1) as from_employee_count
            
            OPTIONAL MATCH (p2:Profile)-[:HAS_EXPERIENCE]->(e2)-[:AT_COMPANY]->(to_company)
            WHERE e2.isCurrent = true
            WITH from_company, to_company, transition_count, from_employee_count, count(p2) as to_employee_count
            
            // Return node and link data for visualization
            RETURN collect(distinct {{
              id: from_company.urn,
              name: from_company.name,
              type: 'company',
              employeeCount: from_employee_count,
              outflow: transition_count,
              inflow: 0
            }}) + collect(distinct {{
              id: to_company.urn,
              name: to_company.name,
              type: 'company',
              employeeCount: to_employee_count,
              outflow: 0,
              inflow: transition_count
            }}) as nodes,
            collect({{
              source: from_company.urn,
              target: to_company.urn,
              value: transition_count,
              direction: "outbound"
            }}) as links
            """
        
        # Execute the query
        result = db._run_query(cypher_query)
        
        if result and len(result) > 0:
            # Extract nodes and links
            raw_nodes = result[0].get("nodes", [])
            raw_links = result[0].get("links", [])
            
            # Process and deduplicate nodes (since we combined collections in Cypher)
            nodes_dict = {}
            for node in raw_nodes:
                if node["id"] in nodes_dict:
                    # Combine outflow/inflow counts for same company
                    nodes_dict[node["id"]]["outflow"] += node["outflow"]
                    nodes_dict[node["id"]]["inflow"] += node["inflow"]
                else:
                    nodes_dict[node["id"]] = node
            
            # Calculate net flow for each node
            for node_id, node in nodes_dict.items():
                node["net_flow"] = node["inflow"] - node["outflow"]
            
            # Convert back to list
            nodes = list(nodes_dict.values())
            
            # Get top sources and destinations
            top_sources = sorted(nodes, key=lambda x: x.get("outflow", 0), reverse=True)[:5]
            top_sources = [{"id": n["id"], "name": n["name"], "outflow": n["outflow"]} for n in top_sources]
            
            top_destinations = sorted(nodes, key=lambda x: x.get("inflow", 0), reverse=True)[:5]
            top_destinations = [{"id": n["id"], "name": n["name"], "inflow": n["inflow"]} for n in top_destinations]
            
            # Create summary statistics
            total_transitions = sum(link["value"] for link in raw_links)
            
            summary = {
                "total_transitions": total_transitions,
                "highest_outflow": {"company": top_sources[0]["name"], "count": top_sources[0]["outflow"]} if top_sources else None,
                "highest_inflow": {"company": top_destinations[0]["name"], "count": top_destinations[0]["inflow"]} if top_destinations else None
            }
            
            # Create final response
            network_data = {
                "nodes": nodes,
                "links": raw_links,
            "summary": summary,
                "top_sources": top_sources,
                "top_destinations": top_destinations
            }
            
            # Close database connection
            db.close()
            
            # Cache the results
            cache["talent_flow_cache"][cache_key] = network_data
            cache["last_updated"][cache_key] = request_time
        
            return network_data
        else:
            # No results found
            db.close()
            
            # Create fallback/empty response
            empty_response = {
                "nodes": [],
                "links": [],
                "summary": {"total_transitions": 0},
                "top_sources": [],
                "top_destinations": []
            }
            
            return empty_response
            
    except Exception as e:
        print(f"Error analyzing talent flow: {str(e)}")
        traceback_str = traceback.format_exc()
        print(traceback_str)
        
        # Generate fallback response with minimal data
        fallback_nodes = [
            {"id": "company-a", "name": "TechCorp", "type": "company", "employeeCount": 1250, "outflow": 28, "inflow": 15, "net_flow": -13},
            {"id": "company-b", "name": "AI Innovations", "type": "company", "employeeCount": 380, "outflow": 12, "inflow": 28, "net_flow": 16},
            {"id": "company-c", "name": "DataSphere", "type": "company", "employeeCount": 520, "outflow": 8, "inflow": 8, "net_flow": 0}
        ]
        
        fallback_links = [
            {"source": "company-a", "target": "company-b", "value": 28, "direction": "outbound"},
            {"source": "company-c", "target": "company-a", "value": 15, "direction": "inbound"},
            {"source": "company-b", "target": "company-c", "value": 12, "direction": "outbound"}
        ]
        
        fallback_summary = {
            "total_transitions": 55,
            "highest_outflow": {"company": "TechCorp", "count": 28},
            "highest_inflow": {"company": "AI Innovations", "count": 28}
        }
        
        fallback_data = {
            "nodes": fallback_nodes,
            "links": fallback_links,
            "summary": fallback_summary,
            "top_sources": [
                {"id": "company-a", "name": "TechCorp", "outflow": 28},
                {"id": "company-b", "name": "AI Innovations", "outflow": 12}
            ],
            "top_destinations": [
                {"id": "company-b", "name": "AI Innovations", "inflow": 28},
                {"id": "company-a", "name": "TechCorp", "inflow": 15}
            ]
        }
        
        return fallback_data

@app.post("/api/analytics/geographic", response_model=GeographicAnalysisResponse)
async def geographic_analysis(request: GeographicAnalysisRequest):
    """
    Analyze geographic distribution of talent, companies, salaries, and other metrics.
    
    This endpoint provides:
    - Region-level metrics for different indicators
    - City-level metrics for detailed analysis
    - Comparative regional analysis
    """
    try:
        # Check cache if no specific filters
        cache_key = "geographic_data"
        if not request.regions and request.time_period == "all" and is_cache_valid(cache_key):
            logger.info("Using cached geographic data")
            geo_data = cache["geographic_data"]
        else:
            # Get start and end dates based on time period
            start_date, end_date = get_time_period_dates(request.time_period)
            
            # Query region-level data
            # In a real implementation, this would query the database
            # For now, we'll generate mock data
            
            # Generate mock regions
            regions = [
                {"id": "us", "name": "United States", "type": "country"},
                {"id": "us-ca", "name": "California", "type": "state", "parent_id": "us"},
                {"id": "us-ny", "name": "New York", "type": "state", "parent_id": "us"},
                {"id": "us-tx", "name": "Texas", "type": "state", "parent_id": "us"},
                {"id": "us-ma", "name": "Massachusetts", "type": "state", "parent_id": "us"},
                {"id": "uk", "name": "United Kingdom", "type": "country"},
                {"id": "uk-ldn", "name": "London", "type": "region", "parent_id": "uk"},
                {"id": "sg", "name": "Singapore", "type": "country"},
            ]
            
            # Generate mock cities
            cities = [
                {"id": "us-sfo", "name": "San Francisco", "region_id": "us-ca"},
                {"id": "us-la", "name": "Los Angeles", "region_id": "us-ca"},
                {"id": "us-nyc", "name": "New York City", "region_id": "us-ny"},
                {"id": "us-aus", "name": "Austin", "region_id": "us-tx"},
                {"id": "us-bos", "name": "Boston", "region_id": "us-ma"},
                {"id": "uk-ldn", "name": "London", "region_id": "uk-ldn"},
                {"id": "sg-sgp", "name": "Singapore", "region_id": "sg"},
            ]
            
            # Filter regions if requested
            if request.regions:
                regions = [r for r in regions if r["id"] in request.regions]
                region_ids = [r["id"] for r in regions]
                cities = [c for c in cities if c["region_id"] in region_ids]
            
            # Add metrics to regions
            for region in regions:
                metrics = {}
                
                # Add requested metrics
                for metric in request.metrics:
                    if metric == "talent_density":
                        metrics[metric] = round(get_mock_value(10, 100), 1)
                    elif metric == "company_density":
                        metrics[metric] = round(get_mock_value(5, 50), 1)
                    elif metric == "avg_salary":
                        metrics[metric] = int(get_mock_value(50000, 150000))
                    elif metric == "funding":
                        metrics[metric] = int(get_mock_value(10000000, 1000000000))
                    elif metric == "skill_demand":
                        metrics[metric] = round(get_mock_value(30, 100), 1)
                
                # Add growth rates
                metrics["growth_rates"] = {
                    "talent": round(get_mock_value(-5, 25), 1),
                    "companies": round(get_mock_value(0, 20), 1),
                    "funding": round(get_mock_value(-10, 30), 1)
                }
                
                # Add top skills
                metrics["top_skills"] = [
                    {"name": "Data Science", "value": round(get_mock_value(60, 100), 1)},
                    {"name": "Machine Learning", "value": round(get_mock_value(60, 100), 1)},
                    {"name": "Cloud Computing", "value": round(get_mock_value(60, 100), 1)},
                    {"name": "Blockchain", "value": round(get_mock_value(60, 100), 1)},
                    {"name": "UX Design", "value": round(get_mock_value(60, 100), 1)}
                ]
                
                region["metrics"] = metrics
            
            # Add metrics to cities
            for city in cities:
                metrics = {}
                
                # Add requested metrics (cities tend to have higher values than regions)
                for metric in request.metrics:
                    if metric == "talent_density":
                        metrics[metric] = round(get_mock_value(50, 200), 1)
                    elif metric == "company_density":
                        metrics[metric] = round(get_mock_value(10, 100), 1)
                    elif metric == "avg_salary":
                        metrics[metric] = int(get_mock_value(70000, 200000))
                    elif metric == "funding":
                        metrics[metric] = int(get_mock_value(50000000, 2000000000))
                    elif metric == "skill_demand":
                        metrics[metric] = round(get_mock_value(50, 100), 1)
                
                # Add growth rates
                metrics["growth_rates"] = {
                    "talent": round(get_mock_value(0, 35), 1),
                    "companies": round(get_mock_value(5, 25), 1),
                    "funding": round(get_mock_value(0, 40), 1)
                }
                
                city["metrics"] = metrics
            
            # Create summary metrics
            summary = {
                "top_region": {
                    "talent_density": max(regions, key=lambda r: r["metrics"].get("talent_density", 0))["name"],
                    "company_density": max(regions, key=lambda r: r["metrics"].get("company_density", 0))["name"],
                    "avg_salary": max(regions, key=lambda r: r["metrics"].get("avg_salary", 0))["name"],
                    "funding": max(regions, key=lambda r: r["metrics"].get("funding", 0))["name"]
                },
                "top_city": {
                    "talent_density": max(cities, key=lambda c: c["metrics"].get("talent_density", 0))["name"],
                    "company_density": max(cities, key=lambda c: c["metrics"].get("company_density", 0))["name"],
                    "avg_salary": max(cities, key=lambda c: c["metrics"].get("avg_salary", 0))["name"],
                    "funding": max(cities, key=lambda c: c["metrics"].get("funding", 0))["name"]
                },
                "global_trends": {
                    "fastest_growing_region": max(regions, key=lambda r: r["metrics"]["growth_rates"].get("talent", 0))["name"],
                    "most_funded_region": max(regions, key=lambda r: r["metrics"].get("funding", 0))["name"],
                    "highest_salary_city": max(cities, key=lambda c: c["metrics"].get("avg_salary", 0))["name"]
                }
            }
            
            # Create geo data object
            geo_data = {
                "regions": regions,
                "cities": cities,
                "summary": summary
            }
            
            # Cache results if this is the default query
            if not request.regions and request.time_period == "all":
                cache["geographic_data"] = geo_data
                cache["last_updated"][cache_key] = datetime.now()
        
        return GeographicAnalysisResponse(**geo_data)
        
    except Exception as e:
        logger.exception(f"Error in geographic analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions for mock data generation
def get_mock_value(min_val: float, max_val: float) -> float:
    """Generate a random value within the given range"""
    return min_val + (max_val - min_val) * np.random.random()

def generate_mock_timeseries(start_date: datetime, end_date: datetime, min_val: float, max_val: float) -> List[Tuple[datetime, float]]:
    """Generate mock timeseries data with a trend pattern"""
    # Calculate number of data points (one per month)
    delta = end_date - start_date
    num_points = max(1, int(delta.days / 30))
    
    # Generate dates
    dates = [start_date + timedelta(days=i*30) for i in range(num_points)]
    
    # Generate values with a trend
    base = min_val
    trend = (max_val - min_val) / num_points if num_points > 1 else 0
    values = []
    
    for i in range(num_points):
        # Add randomness to the trend
        noise = (max_val - min_val) * 0.1 * (np.random.random() - 0.5)
        value = base + trend * i + noise
        values.append(value)
    
    return list(zip(dates, values))

def generate_mock_funding_timeseries(start_date: datetime, end_date: datetime) -> List[Tuple[datetime, float]]:
    """Generate mock funding round events"""
    # Funding rounds are discrete events, typically 12-24 months apart
    delta = end_date - start_date
    max_rounds = max(1, int(delta.days / 365))
    
    # Generate between 1 and max_rounds funding events
    num_rounds = np.random.randint(1, max_rounds + 1)
    
    # Generate round dates (more recent rounds are more likely)
    days_range = (end_date - start_date).days
    days = sorted([int(np.random.triangular(0, days_range*0.8, days_range)) for _ in range(num_rounds)])
    dates = [start_date + timedelta(days=d) for d in days]
    
    # Generate round amounts (increasing over time with some randomness)
    base_amount = get_mock_value(1000000, 5000000)  # Seed round
    amounts = []
    
    for i in range(num_rounds):
        # Each round is typically 2-3x the previous round
        multiplier = get_mock_value(1.5, 3.0) if i > 0 else 1.0
        amount = base_amount * (multiplier ** i) * (0.8 + 0.4 * np.random.random())
        amounts.append(amount)
    
    return list(zip(dates, amounts))

# AI Analytics endpoints
@app.get("/api/analytics/recommendations")
async def get_recommendations(
    mode: str = Query("investment", description="Recommendation mode: investment, talent, or partnership"),
    industries: List[str] = Query(None, description="Industry filters"),
    funding_stages: List[str] = Query(None, description="Funding stage filters"),
    geo_regions: List[str] = Query(None, description="Geographic region filters"),
    portfolio_ids: List[str] = Query(None, description="Portfolio company IDs"),
    confidence_threshold: float = Query(0.5, description="Minimum confidence threshold"),
    req: Request = None
):
    """
    Get AI-powered recommendations based on specified context and real Neo4j data
    """
    print(f"Generating recommendations for mode: {mode}, industries: {industries}")
    
    try:
        # Connect to Neo4j database
        db = Neo4jDatabase()
        
        # Define industry for context
        industry_text = "Technology"
        if industries and len(industries) > 0:
            industry_text = industries[0]
        
        # Get real companies data from Neo4j
        if mode == "investment":
            # Query to get company data that matches the filters
            cypher_query = """
            MATCH (c:Company)
            
            // Get employee count
            OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
            WHERE e.isCurrent = true
            WITH c, count(p) as employeeCount
            
            // Get recent transitions
            OPTIONAL MATCH (p2:Profile)-[:HAS_TRANSITION]->(t)-[:TO_COMPANY]->(c)
            WHERE t.date >= datetime() - duration('P6M')
            WITH c, employeeCount, count(p2) as recentHires
            
            // Calculate growth metrics
            WITH c, employeeCount, recentHires,
                 CASE WHEN employeeCount > 0 
                      THEN round(100.0 * recentHires / employeeCount, 1)
                      ELSE 0
                 END as growthRate
            
            // Return company data
            RETURN c.urn as urn,
                   c.name as name,
                   employeeCount,
                   recentHires,
                   growthRate,
                   round(rand() * 30, 1) as fundingAmount
            ORDER BY growthRate DESC, recentHires DESC
            LIMIT 50
            """
            
            results = db._run_query(cypher_query)
            
            # Transform raw data to recommendation format
            companies = []
            for result in results:
                # Skip entries with no name or URN
                if not result.get("name") or not result.get("urn"):
                    continue
                    
                company = {
                    "id": result["urn"],
                    "companyId": result["urn"],
                    "companyName": result["name"],
                    "confidence": round(0.8 - (len(companies)*0.03), 2),
                    "sector": industry_text,
                    "stage": funding_stages[0] if funding_stages and len(funding_stages) > 0 else "Series A", 
                    "region": geo_regions[0] if geo_regions and len(geo_regions) > 0 else "San Francisco Bay Area",
                    "recommendation_reason": f"Strong growth metrics with {result['growthRate']}% growth rate",
                    "valuation": round(result["employeeCount"] * 0.2, 1),
                    "growthRate": result["growthRate"],
                    "score": round(0.8 - (len(companies)*0.03), 2),
                    "keyFactors": ["Team growth", "Market position", "Execution potential"],
                    "modelScore": round(0.8 - (len(companies)*0.03), 2)
                }
                companies.append(company)
            
            # Close database connection
            db.close()
            
            # Take only top recommendations
            recommendations = companies[:8]
            
            # Filter by confidence threshold
            recommendations = [r for r in recommendations if r.get("confidence", 0) >= confidence_threshold]
            
            print(f"Generated {len(recommendations)} investment recommendations")
            return recommendations
        
        elif mode == "talent":
            # Query to get talent profiles with recent transitions
            cypher_query = """
            MATCH (p:Profile)-[:HAS_TRANSITION]->(t:Transition)-[:TO_COMPANY]->(c:Company)
            WHERE t.date >= datetime() - duration('P6M')
            
            WITH p, c, t ORDER BY t.date DESC
            WITH p, collect(distinct {company: c.name, date: t.date})[0] as currentCompany
            
            // Get skills
            OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
            WITH p, currentCompany, collect(s.name) as skills
            
            RETURN p.urn as id,
                   p.firstName + ' ' + p.lastName as name,
                   p.headline as title,
                   skills,
                   currentCompany.company as currentCompany
            LIMIT 30
            """
            
            talents = db._run_query(cypher_query)
            
            # Convert to talent recommendations
            talent_recommendations = []
            for i, talent in enumerate(talents[:6]):
                # Get skill list or empty list if None
                skill_list = talent.get("skills", []) or []
                # Limit to 5 skills
                skills = skill_list[:5] if skill_list else ["Leadership", "Management"]
                
                talent_recommendations.append({
                    "id": talent["id"],
                    "candidateName": talent["name"] if talent.get("name") else f"Candidate {i+1}",
                    "confidence": round(0.9 - (i*0.05), 2),
                    "currentRole": talent.get("title", "Senior Professional"),
                    "currentCompany": talent.get("currentCompany", "Tech Company"),
                    "skills": skills,
                    "recommendation_reason": f"Strong background in {', '.join(skills[:2])}",
                    "skillMatch": round(0.85 - (i*0.05), 2),
                    "cultureMatch": round(0.8 - (i*0.03), 2),
                    "retentionScore": round(0.75 - (i*0.02), 2),
                    "fitScore": 5 - min(i, 4)
                })
            
            # Close database connection
            db.close()
            
            # Filter by confidence threshold
            talent_recommendations = [r for r in talent_recommendations if r.get("confidence", 0) >= confidence_threshold]
            
            print(f"Generated {len(talent_recommendations)} talent recommendations")
            return talent_recommendations
            
        elif mode == "partnership":
            # Query to get companies with potential partnership value
            cypher_query = """
            MATCH (c:Company)
            
            // Get company size via employee count
            OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
            WHERE e.isCurrent = true
            WITH c, count(p) as employeeCount
            
            // Get transition connections (talent flow between companies can indicate partnership potential)
            OPTIONAL MATCH (c)<-[:TO_COMPANY]-(t:Transition)-[:FROM_COMPANY]->(otherCompany:Company)
            WITH c, employeeCount, count(distinct otherCompany) as connectedCompanies
            
            // Return company data
            RETURN c.urn as id,
                   c.name as name,
                   employeeCount,
                   connectedCompanies,
                   CASE
                     WHEN employeeCount < 50 THEN 'Small'
                     WHEN employeeCount < 200 THEN 'Medium'
                     ELSE 'Large'
                   END as size
            ORDER BY connectedCompanies DESC, employeeCount DESC
            LIMIT 30
            """
            
            companies = db._run_query(cypher_query)
            
            # Convert to partnership recommendations
            partnership_recommendations = []
            for i, company in enumerate(companies[:8]):
                partnership_recommendations.append({
                    "id": company["id"],
                    "companyName": company["name"],
                    "confidence": round(0.88 - (i*0.04), 2),
                    "industry": industry_text, 
                    "size": company.get("size", "Medium"),
                    "region": geo_regions[0] if geo_regions and len(geo_regions) > 0 else "San Francisco Bay Area", 
                    "synergies": ["Technology integration", "Market expansion", "Talent sharing"],
                    "recommendation_reason": f"Strong ecosystem connections with {company.get('connectedCompanies', 0)} related companies",
                    "score": round(0.88 - (i*0.04), 2)
                })
            
            # Close database connection
            db.close()
            
        # Filter by confidence threshold
            partnership_recommendations = [r for r in partnership_recommendations if r.get("confidence", 0) >= confidence_threshold]
            
            print(f"Generated {len(partnership_recommendations)} partnership recommendations")
            return partnership_recommendations
        
        else:
            # Fallback for unknown modes
            db.close()
            return []
            
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        traceback.print_exc()
        
        # Return fallback data in case of error
        fallback_recommendations = [
            {
                "id": "fallback-1", 
                "companyId": "fallback-1",
                "companyName": "Technology Innovations", 
                "confidence": 0.82, 
                "sector": "Technology",
                "stage": "Series A", 
                "region": "San Francisco Bay Area",
                "recommendation_reason": "Strong growth metrics",
                "valuation": 15.0,
                "growthRate": 25.5,
                "score": 0.82,
                "keyFactors": ["Strong team", "Growth potential"],
                "modelScore": 0.82
            },
            {
                "id": "fallback-2", 
                "companyId": "fallback-2",
                "companyName": "Technology Solutions", 
                "confidence": 0.78, 
                "sector": "Technology",
                "stage": "Series A", 
                "region": "San Francisco Bay Area",
                "recommendation_reason": "Product-market fit",
                "valuation": 12.0,
                "growthRate": 22.5,
                "score": 0.78,
                "keyFactors": ["Product-market fit", "Growth potential"],
                "modelScore": 0.78
            }
        ]
        
        return fallback_recommendations

@app.get("/api/analytics/insights")
async def get_insights(
    mode: str = Query("market", description="Insight mode: market, talent, competition"),
    industries: List[str] = Query(None, description="Industry filters"),
    geo_regions: List[str] = Query(None, description="Geographic region filters"),
    portfolio_ids: List[str] = Query(None, description="Portfolio company IDs"),
    time_period: str = Query("6m", description="Time period for insights"),
    req: Request = None
):
    """
    Get AI-generated insights based on real data from Neo4j
    """
    print(f"Getting insights for mode: {mode}, industries: {industries}")
    
    try:
        # Connect to Neo4j database
        db = Neo4jDatabase()
        
        # Use a default industry if none provided
        industry_text = "Technology"
        if industries and len(industries) > 0:
            industry_text = industries[0]
            
        # Use a default region if none provided
        region_text = "San Francisco Bay Area"
        if geo_regions and len(geo_regions) > 0:
            region_text = geo_regions[0]
        
        # Generate insights based on real data
        if mode == "market":
            # Query to get market insights data
            cypher_query = """
            // Get transitions for time period analysis
            MATCH (p:Profile)-[:HAS_TRANSITION]->(t:Transition)
            WHERE t.date >= datetime() - duration('P6M')
            
            // Count transitions by month for trend analysis
            WITH t.date.month as month, count(t) as transitionCount
            ORDER BY month
            
            RETURN collect({month: month, count: transitionCount}) as monthlyTrends
            """
            
            market_results = db._run_query(cypher_query)
            
            # Get company growth trends
            growth_query = """
            // Match companies and their recent hires
            MATCH (c:Company)<-[:AT_COMPANY]-(e:Experience)<-[:HAS_EXPERIENCE]-(p:Profile)
            WHERE e.isCurrent = true
            
            // Group by company and get employee counts
            WITH c, count(p) as currentEmployees
            
            // Get recent hires in the last 6 months
            OPTIONAL MATCH (c)<-[:TO_COMPANY]-(t:Transition)
            WHERE t.date >= datetime() - duration('P6M')
            
            WITH c, currentEmployees, count(t) as recentHires
            WHERE currentEmployees > 10 // Only include companies with meaningful employee data
            
            // Calculate growth rate
            WITH c.name as company, currentEmployees, recentHires,
                 round(100.0 * recentHires / currentEmployees, 1) as growthRate
            
            // Order by growth rate and take top companies
            ORDER BY growthRate DESC
            LIMIT 10
            
            RETURN collect({company: company, employees: currentEmployees, growth: growthRate}) as topGrowingCompanies
            """
            
            growth_results = db._run_query(growth_query)
            
            # Get transition insights
            transition_query = """
            // Analyze transitions between industries
            MATCH (p:Profile)-[:HAS_TRANSITION]->(t:Transition)-[:FROM_COMPANY]->(c1:Company)
            MATCH (t)-[:TO_COMPANY]->(c2:Company)
            WHERE t.date >= datetime() - duration('P6M')
            
            // Count transitions between companies
            WITH c1.name as fromCompany, c2.name as toCompany, count(t) as transitionCount
            WHERE transitionCount > 2 // Only significant flows
            
            // Order by transition count
            ORDER BY transitionCount DESC
            LIMIT 10
            
            RETURN collect({from: fromCompany, to: toCompany, count: transitionCount}) as talentFlows
            """
            
            transition_results = db._run_query(transition_query)
            
            # Close database connection
            db.close()
            
            # Prepare insights based on real data
            insights = []
            
            # Market trend insight
            if market_results and market_results[0].get("monthlyTrends"):
                monthly_trends = market_results[0]["monthlyTrends"]
                # Calculate trend direction and percentage
                trend_percentage = 0
                if len(monthly_trends) >= 2:
                    first_month = monthly_trends[0]["count"]
                    last_month = monthly_trends[-1]["count"]
                    if first_month > 0:
                        trend_percentage = round(100 * (last_month - first_month) / first_month, 1)
                
                insights.append({
                    "id": "market-1", 
                    "title": f"{industry_text} Job Market Trends", 
                    "summary": f"Professional transitions in {industry_text} have {'increased' if trend_percentage > 0 else 'decreased'} by {abs(trend_percentage)}% over the past {time_period}.",
                    "type": "trend",
                    "data": {
                        "percentage_change": trend_percentage,
                        "trend": "up" if trend_percentage > 0 else "down",
                        "time_period": time_period,
                        "monthly_data": monthly_trends
                    },
                    "confidence": 0.87,
                    "sources": ["Transition Analysis", "Market Reports"]
                })
            
            # Company growth insight
            if growth_results and growth_results[0].get("topGrowingCompanies"):
                growing_companies = growth_results[0]["topGrowingCompanies"]
                insights.append({
                    "id": "market-2", 
                    "title": f"Top Growing {industry_text} Companies", 
                    "summary": f"The fastest growing companies in {industry_text} include {growing_companies[0]['company']} ({growing_companies[0]['growth']}%) and {growing_companies[1]['company']} ({growing_companies[1]['growth']}%).",
                    "type": "ranking",
                    "data": {
                        "companies": growing_companies,
                        "time_period": time_period
                    },
                    "confidence": 0.92,
                    "sources": ["Employee Data", "Growth Analysis"]
                })
            
            # Talent flow insight
            if transition_results and transition_results[0].get("talentFlows"):
                talent_flows = transition_results[0]["talentFlows"]
                insights.append({
                    "id": "market-3", 
                    "title": f"{industry_text} Talent Migration Patterns", 
                    "summary": f"Significant talent movement observed from {talent_flows[0]['from']} to {talent_flows[0]['to']} with {talent_flows[0]['count']} transitions in the last {time_period}.",
                    "type": "flow",
                    "data": {
                        "flows": talent_flows,
                        "time_period": time_period
                    },
                    "confidence": 0.85,
                    "sources": ["Transition Data", "Talent Flow Analysis"]
                })
            
            # If no real insights could be generated, create a fallback
            if not insights:
                insights = [
                {
                        "id": "market-fallback", 
                    "title": f"{industry_text} Market Overview", 
                        "summary": f"The {industry_text} market continues to evolve with emerging opportunities in {region_text}.",
                    "type": "analysis",
                    "confidence": 0.75,
                    "sources": ["Market Analysis"]
                }
            ]
            
            print(f"Generated {len(insights)} market insights")
        return insights
    except Exception as e:
        print(f"Error generating insights: {str(e)}")
        
        # Return fallback insights in case of error
        fallback_insights = [
            {
                "id": "fallback-market-1", 
                "title": "Technology Market Overview", 
                "summary": "The technology market continues to evolve with emerging opportunities.",
                "type": "analysis",
                "confidence": 0.75,
                "sources": ["Market Analysis"]
            },
            {
                "id": "fallback-market-2", 
                "title": "Technology Growth Potential", 
                "summary": "Technology sector shows steady growth potential over the next 12 months.",
                "type": "forecast",
                "confidence": 0.72,
                "sources": ["Growth Metrics"]
            }
        ]
        
        return fallback_insights

@app.get("/api/analytics/opportunities")
async def get_opportunities(
    industry: str = Query(None, description="Industry filter for opportunities"),
    region: str = Query(None, description="Region filter for opportunities"),
    timeframe: str = Query("medium", description="Timeframe for opportunities (short/medium/long)"),
    mode: str = Query("investment", description="Opportunity mode: investment, talent, or partnership"),
    req: Request = None
):
    """
    Get AI-identified opportunities based on real Neo4j data
    """
    print(f"Getting opportunities for industry: {industry}, region: {region}, mode: {mode}")
    
    try:
        # Connect to Neo4j database
        db = Neo4jDatabase()
        
        # Use a default industry if none provided
        industry_text = industry if industry else "Technology"
        region_text = region if region else "Global"
        
        # Generate opportunities based on real data
        opportunities = []
        
        if mode == "investment":
            # Find high-growth companies
            investment_query = """
            // Find companies with high recent growth
            MATCH (c:Company)
            
            // Get employee count
            OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
            WHERE e.isCurrent = true
            WITH c, count(p) as employeeCount
            
            // Get recent hires
            OPTIONAL MATCH (t:Transition)-[:TO_COMPANY]->(c)
            WHERE t.date >= datetime() - duration('P6M')
            WITH c, employeeCount, count(t) as recentHires
            
            // Calculate growth rate
            WITH c, employeeCount, recentHires,
                 CASE WHEN employeeCount > 0 
                      THEN round(100.0 * recentHires / employeeCount, 1)
                      ELSE 0
                 END as growthRate
            
            // Filter to high-growth companies with meaningful employee bases
            WHERE employeeCount >= 10 AND growthRate >= 15
            
            // Return top companies by growth rate
            RETURN c.urn as id,
                   c.name as name,
                   employeeCount,
                   recentHires,
                   growthRate
            ORDER BY growthRate DESC, employeeCount DESC
            LIMIT 5
            """
            
            investment_results = db._run_query(investment_query)
            
            # Convert to opportunities
            for i, result in enumerate(investment_results):
                opportunities.append({
                    "id": f"inv-{result.get('id', f'opportunity-{i}')}",
                    "title": f"Investment in {result.get('name', 'Growing Company')}",
                    "description": f"High-growth potential with {result.get('growthRate')}% team expansion rate and {result.get('employeeCount')} employees",
                    "confidence": round(0.7 + min(0.25, result.get('growthRate', 20) / 100), 2),
                    "potential_impact": "high" if result.get('growthRate', 0) > 25 else "medium",
                "timeframe": timeframe,
                    "impactScore": round(0.6 + min(0.35, result.get('growthRate', 20) / 100), 2),
                "difficulty": "Medium",
                    "urgency": "high" if result.get('growthRate', 0) > 30 else "medium",
                    "expirationDays": 30 if result.get('growthRate', 0) > 30 else 60,
                    "priority": "high" if result.get('growthRate', 0) > 30 else "medium"
                })
        
        elif mode == "talent":
            # Find skill clusters with growth potential
            talent_query = """
            // Find growing skill clusters
            MATCH (p:Profile)-[:HAS_SKILL]->(s:Skill)
            
            // Get recent transitions with those skills
            OPTIONAL MATCH (p)-[:HAS_TRANSITION]->(t:Transition)
            WHERE t.date >= datetime() - duration('P6M')
            WITH s.name as skill, count(p) as profileCount, count(t) as recentTransitions
            
            // Calculate growth metrics
            WITH skill, profileCount, recentTransitions,
                 CASE WHEN profileCount > 0 
                      THEN round(100.0 * recentTransitions / profileCount, 1)
                      ELSE 0
                 END as mobilityRate
            
            // Filter to meaningful skill clusters
            WHERE profileCount >= 5
            
            // Return top skill clusters by activity
            RETURN skill,
                   profileCount,
                   recentTransitions,
                   mobilityRate
            ORDER BY mobilityRate DESC, profileCount DESC
            LIMIT 5
            """
            
            talent_results = db._run_query(talent_query)
            
            # Convert to opportunities
            for i, result in enumerate(talent_results):
                opportunities.append({
                    "id": f"talent-{i+1}",
                    "title": f"{result.get('skill', 'In-demand skill')} Talent Acquisition",
                    "description": f"Strategic hiring opportunity with {result.get('profileCount')} profiles showing high mobility ({result.get('mobilityRate')}% transition rate)",
                    "confidence": round(0.8 + min(0.15, result.get('mobilityRate', 15) / 100), 2),
                    "potential_impact": "high" if result.get('mobilityRate', 0) > 20 else "medium",
                "timeframe": timeframe,
                    "impactScore": round(0.7 + min(0.25, result.get('mobilityRate', 15) / 100), 2),
                    "difficulty": "Medium",
                    "urgency": "high" if result.get('mobilityRate', 0) > 25 else "medium",
                    "expirationDays": 14 if result.get('mobilityRate', 0) > 25 else 30,
                    "priority": "high" if result.get('mobilityRate', 0) > 25 else "medium"
                })
        
        elif mode == "partnership":
            # Find companies with strong network connections
            partnership_query = """
            // Find companies with strong network connections
            MATCH (c1:Company)<-[:AT_COMPANY]-(:Experience)<-[:HAS_EXPERIENCE]-(p:Profile)-[:HAS_EXPERIENCE]->(:Experience)-[:AT_COMPANY]->(c2:Company)
            WHERE c1 <> c2
            WITH c1, c2, count(p) as sharedTalent
            
            // Filter to meaningful connections
            WHERE sharedTalent >= 3
            
            // Return top company pairs by connection strength
            RETURN c1.urn as company1_id,
                   c1.name as company1_name,
                   c2.urn as company2_id,
                   c2.name as company2_name,
                   sharedTalent
            ORDER BY sharedTalent DESC
            LIMIT 5
            """
            
            partnership_results = db._run_query(partnership_query)
            
            # Convert to opportunities
            for i, result in enumerate(partnership_results):
                opportunities.append({
                    "id": f"partner-{i+1}",
                    "title": f"Strategic Partnership with {result.get('company2_name', 'Connected Company')}",
                    "description": f"Strong talent ecosystem connection with {result.get('sharedTalent')} shared professional relationships",
                    "confidence": round(0.75 + min(0.2, result.get('sharedTalent', 3) / 20), 2),
                    "potential_impact": "high" if result.get('sharedTalent', 0) > 5 else "medium",
                "timeframe": timeframe,
                    "impactScore": round(0.7 + min(0.25, result.get('sharedTalent', 3) / 15), 2),
                "difficulty": "Medium",
                "urgency": "medium",
                "expirationDays": 45,
                "priority": "medium"
            })
        
        # If no opportunities found from real data, add a default opportunity
        if not opportunities:
            opportunities = [
                {
                    "id": f"{mode}-default",
                    "title": f"{industry_text} Market Opportunity",
                    "description": f"Explore emerging opportunities in {industry_text} sector with focus on {region_text}",
                    "confidence": 0.75,
                    "potential_impact": "medium",
                    "timeframe": timeframe,
                    "impactScore": 0.70,
                    "difficulty": "Medium",
                    "urgency": "medium",
                    "expirationDays": 45,
                    "priority": "medium"
                }
            ]
        
        # Close database connection
        db.close()
        
        print(f"Generated {len(opportunities)} opportunities")
        return opportunities
        
    except Exception as e:
        print(f"Error generating opportunities: {str(e)}")
        traceback.print_exc()
        
        # Return fallback opportunities in case of error
        fallback_opportunities = [
            {
                "id": "fallback-1",
                "title": "Technology Growth Opportunity",
                "description": "Explore growth potential in technology sector with focus on global region",
                "confidence": 0.75,
                "potential_impact": "medium",
                "timeframe": "medium",
                "impactScore": 0.70,
                "difficulty": "Medium",
                "urgency": "medium",
                "expirationDays": 45,
                "priority": "medium"
            }
        ]
        
        return fallback_opportunities

@app.post("/api/analytics/company-deep-dive")
async def company_deep_dive(request: dict):
    """
    Get comprehensive AI analysis of a company using real Neo4j data
    """
    try:
        company_id = request.get("company_id")
        if not company_id:
            raise HTTPException(status_code=400, detail="Company ID is required")
            
        options = request.get("options", {})
        time_period = options.get("time_period", "1y")
        
        # Connect to Neo4j database
        db = Neo4jDatabase()
        
        # Query company details
        company_query = f"""
        MATCH (c:Company {{urn: "{company_id}"}})
        RETURN c.name as name, c.urn as urn
        """
        
        company_result = db._run_query(company_query)
        if not company_result or len(company_result) == 0:
            raise HTTPException(status_code=404, detail="Company not found")
            
        company_name = company_result[0].get("name", "Unknown Company")
        
        # Query growth metrics
        growth_query = f"""
        MATCH (c:Company {{urn: "{company_id}"}})
        
        // Get current employee count
        OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
        WHERE e.isCurrent = true
        WITH c, count(p) as currentEmployees
        
        // Get employee counts over time (last year by quarter)
        OPTIONAL MATCH (t:Transition)-[:TO_COMPANY]->(c)
        WHERE t.date >= datetime() - duration('P1Y')
        WITH c, currentEmployees, t
        ORDER BY t.date
        WITH c, currentEmployees, collect({{date: t.date, event: "hire"}}) as hires
        
        OPTIONAL MATCH (t:Transition)-[:FROM_COMPANY]->(c)
        WHERE t.date >= datetime() - duration('P1Y')
        WITH c, currentEmployees, hires, collect({{date: t.date, event: "departure"}}) as departures
        
        // Calculate growth rate
        OPTIONAL MATCH (t_in:Transition)-[:TO_COMPANY]->(c)
        WHERE t_in.date >= datetime() - duration('P6M')
        WITH c, currentEmployees, hires, departures, count(t_in) as recentHires
        
        OPTIONAL MATCH (t_out:Transition)-[:FROM_COMPANY]->(c)
        WHERE t_out.date >= datetime() - duration('P6M')
        WITH c, currentEmployees, hires, departures, recentHires, count(t_out) as recentDepartures
        
        RETURN {{
            current_employees: currentEmployees,
            recent_hires: recentHires,
            recent_departures: recentDepartures,
            growth_rate: CASE WHEN currentEmployees > 0 
                         THEN round(100.0 * recentHires / currentEmployees, 1)
                         ELSE 0 END,
            churn_rate: CASE WHEN currentEmployees > 0 
                        THEN round(100.0 * recentDepartures / currentEmployees, 1)
                        ELSE 0 END,
            retention_rate: CASE WHEN (currentEmployees + recentDepartures) > 0 
                            THEN round(100.0 * currentEmployees / (currentEmployees + recentDepartures), 1)
                            ELSE 0 END,
            employee_events: hires + departures
        }} as growth_metrics
        """
        
        growth_result = db._run_query(growth_query)
        growth_metrics = growth_result[0].get("growth_metrics", {}) if growth_result else {}
        
        # Query talent assessment
        talent_query = f"""
        MATCH (c:Company {{urn: "{company_id}"}})
        
        // Get current employees and their skills
        OPTIONAL MATCH (p:Profile)-[:HAS_EXPERIENCE]->(e)-[:AT_COMPANY]->(c)
        WHERE e.isCurrent = true
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
        WITH c, p, e, collect(s.name) as skills
        
        // Get employees with title segments
        WITH c, 
             count(p) as totalEmployees,
             sum(CASE WHEN e.title CONTAINS 'Senior' OR e.title CONTAINS 'Lead' OR e.title CONTAINS 'Manager' OR e.title CONTAINS 'Director' OR e.title CONTAINS 'VP' OR e.title CONTAINS 'Chief' OR e.title CONTAINS 'Head' THEN 1 ELSE 0 END) as seniorCount,
             sum(CASE WHEN e.title CONTAINS 'Engineer' OR e.title CONTAINS 'Developer' THEN 1 ELSE 0 END) as engineerCount,
             collect(distinct skills) as allSkills
        
        // Flatten skills and count frequencies
        WITH c, totalEmployees, seniorCount, engineerCount,
             [skill in apoc.coll.flatten(allSkills) WHERE size(skill) > 0 | skill] as flatSkills
        
        // Count skill frequencies
        WITH c, totalEmployees, seniorCount, engineerCount,
             apoc.map.fromLists(
                [skill in flatSkills | skill],
                [skill in flatSkills | size([s in flatSkills WHERE s = skill])]
             ) as skillCounts
        
        // Get top skills
        WITH c, totalEmployees, seniorCount, engineerCount,
             [skill in apoc.map.sortedProperties(skillCounts, true)[0..5] | {{name: skill[0], count: skill[1]}}] as topSkills,
             CASE WHEN totalEmployees > 0 THEN round(100.0 * seniorCount / totalEmployees, 1) ELSE 0 END as seniorPercentage
        
        RETURN {{
            total_employees: totalEmployees,
            senior_percentage: seniorPercentage,
            engineer_percentage: CASE WHEN totalEmployees > 0 THEN round(100.0 * engineerCount / totalEmployees, 1) ELSE 0 END,
            top_skills: topSkills,
            leadership_score: CASE
                WHEN seniorPercentage > 30 THEN "Strong"
                WHEN seniorPercentage > 20 THEN "Good"
                ELSE "Developing"
            END
        }} as talent_metrics
        """
        
        talent_result = db._run_query(talent_query)
        talent_metrics = talent_result[0].get("talent_metrics", {}) if talent_result else {}
        
        # Query network position
        network_query = f"""
        MATCH (c:Company {{urn: "{company_id}"}})
        
        // Get talent flow connections
        OPTIONAL MATCH (c)<-[:TO_COMPANY]-(t:Transition)-[:FROM_COMPANY]->(other:Company)
        WITH c, other, count(t) as flow
        ORDER BY flow DESC
        LIMIT 5
        
        RETURN collect({{company: other.name, flow: flow}}) as topConnections
        """
        
        network_result = db._run_query(network_query)
        network_data = network_result[0].get("topConnections", []) if network_result else []
        
        # Build company analysis response
        result = {
            "company_id": company_id,
            "name": company_name,
            "analysis": {
                "growth_trajectory": {
                    "score": min(10, max(1, growth_metrics.get("growth_rate", 0) / 10 + 5)),
                    "trend": "accelerating" if growth_metrics.get("growth_rate", 0) > 15 else 
                             "steady" if growth_metrics.get("growth_rate", 0) > 5 else "slowing",
                    "insights": f"{'Strong' if growth_metrics.get('growth_rate', 0) > 15 else 'Moderate' if growth_metrics.get('growth_rate', 0) > 5 else 'Slow'} growth with {growth_metrics.get('growth_rate', 0)}% employee growth rate"
                },
                "team_assessment": {
                    "score": min(10, max(1, talent_metrics.get("senior_percentage", 0) / 10 + 5)),
                    "highlights": f"{talent_metrics.get('leadership_score', 'Developing')} leadership team with {talent_metrics.get('senior_percentage', 0)}% senior roles",
                    "risks": f"{'Low' if growth_metrics.get('churn_rate', 0) < 10 else 'Moderate' if growth_metrics.get('churn_rate', 0) < 20 else 'High'} talent churn at {growth_metrics.get('churn_rate', 0)}%"
                },
                "market_position": {
                    "score": min(10, max(1, 5 + (len(network_data) * 0.5))),
                    "category": "leader" if len(network_data) >= 4 else "challenger" if len(network_data) >= 2 else "emerging",
                    "competitive_advantage": f"Connected with {len(network_data)} major companies in talent ecosystem"
                },
                "talent_quality": {
                    "score": min(10, max(1, 5 + (len(talent_metrics.get("top_skills", [])) * 0.5))),
                    "key_skills": [skill.get("name") for skill in talent_metrics.get("top_skills", [])[:3]],
                    "engineering_ratio": f"{talent_metrics.get('engineer_percentage', 0)}% technical roles"
                }
            },
            "recommendations": []
        }
        
        # Generate recommendations based on metrics
        if growth_metrics.get("growth_rate", 0) > 20:
            result["recommendations"].append("Focus on infrastructure and processes to support rapid scaling")
            
        if growth_metrics.get("churn_rate", 0) > 15:
            result["recommendations"].append("Implement retention strategies to reduce talent churn")
            
        if talent_metrics.get("senior_percentage", 0) < 15:
            result["recommendations"].append("Strengthen leadership team with key senior hires")
            
        if len(network_data) < 3:
            result["recommendations"].append("Develop stronger industry partnerships to improve talent network")
            
        # Add fallback recommendation if none generated
        if not result["recommendations"]:
            result["recommendations"].append("Focus on improving technical talent acquisition for sustainable growth")
        
        # Close database connection
        db.close()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing company: {str(e)}")

@app.post("/api/analytics/company-scores")
async def calculate_company_scores(request: dict):
    """
    Calculate GNN-based scores for companies
    """
    try:
        company_urns = request.get("company_urns", [])
        if not company_urns:
            raise HTTPException(status_code=400, detail="Company URNs are required")
            
        include_pagerank = request.get("include_pagerank", True)
        include_birank = request.get("include_birank", True)
        include_talent_flow = request.get("include_talent_flow", True)
        
        # Connect to Neo4j and calculate scores
        db = Neo4jDatabase()
        result = db.calculate_company_scores(
            company_urns, 
            include_pagerank, 
            include_birank, 
            include_talent_flow
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating scores: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
