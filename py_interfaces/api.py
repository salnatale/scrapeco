from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union, Literal, Tuple
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

# Import custom modules
from parser import (
    raw_text_from_upload,
    text_to_profile,
    transitions_from_profile,
    check_companies,
)
from models import LinkedInProfile, LinkedInCompany, TransitionEvent
from neo4j_database import (
    Neo4jDatabase,
    send_to_neo4j,
    send_transition_to_neo4j,
    query_neo4j,
    Neo4jProfileAnalyzer
)
from druid_database import send_to_druid, send_transition_update
from main import LinkedInAPI
from mock_enhanced import LinkedInDataGenerator
from security import verify_api_key, get_current_user, User, oauth2_scheme

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("enhanced_api")

# Initialize the FastAPI app
app = FastAPI(
    title="Enhanced LinkedIn Analytics API",
    description="Advanced API for LinkedIn data processing, analytics, and insights",
    version="2.0.0",
)

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database connections
neo4j_db = Neo4jDatabase()
profile_analyzer = Neo4jProfileAnalyzer()

# Initialize LinkedIn API client
linkedin_api = None

# GNN components
gnn_trainer = None  # Training orchestrator
gnn_model = None    # Loaded inference model
infra = None        # GNN infrastructure instance

# Cache for frequently accessed data
cache = {
    "company_scores": {},
    "talent_flow_network": None,
    "geographic_data": None,
    "skills_trends": None,
    "last_updated": {},
}

# ─────────────────── Pydantic request/response models ─────────────────────────

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


class TrainRequest(BaseModel):
    snapshot_date: datetime = Field(..., description="Graph snapshot date (YYYY-MM-DD)")
    horizon_years: int = Field(5, description="Prediction horizon in years")
    hyperparams: Dict = Field(
        default_factory=dict, description="Optional training hyperparameters"
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

# Additional request models for VC functionality
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

#
# ─── Singletons ───────────────────────────────────────────────────────────────
#
gnn_trainer = None  # your training orchestrator
gnn_model = None  # loaded inference model
infra = None  # your GNN infrastructure instance

# Helper functions
def get_time_period_dates(time_period: str) -> Tuple[datetime, datetime]:
    """
    Convert a time period string to start and end dates.
    
    Args:
        time_period: One of '1m', '3m', '6m', '1y', 'all'
        
    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    
    if time_period == "1m":
        start_date = end_date - timedelta(days=30)
    elif time_period == "3m":
        start_date = end_date - timedelta(days=90)
    elif time_period == "6m":
        start_date = end_date - timedelta(days=180)
    elif time_period == "1y":
        start_date = end_date - timedelta(days=365)
    else:  # "all"
        start_date = end_date - timedelta(days=3650)  # ~10 years
    
    return start_date, end_date

def is_cache_valid(cache_key: str, max_age_minutes: int = 30) -> bool:
    """
    Check if a cache entry is still valid.
    
    Args:
        cache_key: The key in the cache dictionary
        max_age_minutes: Maximum age in minutes for the cache to be valid
        
    Returns:
        True if cache is valid, False otherwise
    """
    if cache_key not in cache or cache_key not in cache["last_updated"]:
        return False
    
    last_updated = cache["last_updated"].get(cache_key)
    if not last_updated:
        return False
    
    age = datetime.now() - last_updated
    return age.total_seconds() < (max_age_minutes * 60)

def format_number(value: float) -> str:
    """
    Format a number for display, using K, M, B suffixes.
    
    Args:
        value: The number to format
        
    Returns:
        Formatted string
    """
    if value < 1000:
        return str(value)
    elif value < 1000000:
        return f"{value/1000:.1f}K"
    elif value < 1000000000:
        return f"{value/1000000:.1f}M"
    else:
        return f"{value/1000000000:.1f}B"

# Routes for health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "LinkedIn Data API is running"}


# ─── Ingest Dataset Endpoints ────────────────────────────────────────────────
#


@app.post("/api/process_corpus")
async def process_corpus(folder_path: str):
    """
    Process a local folder of .txt files and batch store parsed LinkedIn profiles and transitions.
    Each file is expected to be plain text.
    """
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder path not found")

    file_paths = glob.glob(os.path.join(folder_path, "*.txt"))
    if not file_paths:
        raise HTTPException(
            status_code=404, detail="No .txt files found in the directory"
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
    (Re)create the collapsed Employee ↔ Company projection in GDS.
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
        "success": True,
        "filename": file.filename,
        "path": file_path,
        "message": "LinkedIn screenshot uploaded successfully. Processing will occur asynchronously.",
    }


# ─── TRAINING & MODEL MANAGEMENT ────────────────────────────────────────────────
#
@app.post("/gnn/train", response_model=TrainResponse)
async def train_gnn(req: TrainRequest):
    job_id = str(uuid4())
    # kick off: gnn_trainer.start(job_id, req.snapshot_date, req.horizon_years, req.hyperparams)
    return TrainResponse(job_id=job_id)


@app.post("/gnn/model/reload")
async def reload_model():
    global gnn_model
    # gnn_model = gnn_trainer.load_latest()
    return {"status": "model reloaded"}


#
# ─── INFERENCE ───────────────────────────────────────────────────────────────────
#
@app.get("/gnn/predict/company/{company_id}", response_model=PredictCompanyResponse)
async def predict_company(company_id: str):
    if gnn_model is None:
        raise HTTPException(503, "Model not loaded")
    # score = gnn_model.predict_single(company_id)
    score = 0.0
    return PredictCompanyResponse(company_id=company_id, score=score)


@app.post("/gnn/predict/companies", response_model=PredictCompaniesResponse)
async def predict_companies(req: PredictCompaniesRequest):
    if gnn_model is None:
        raise HTTPException(503, "Model not loaded")
    # scores = gnn_model.predict_batch(req.company_ids)
    scores = {cid: 0.0 for cid in req.company_ids}
    return PredictCompaniesResponse(scores=scores)


#
# ─── GRAPH INGESTION & REFRESH ───────────────────────────────────────────────────
#
@app.post("/gnn/graph/ingest", status_code=204)
async def ingest_node(req: IngestNodeRequest):
    """
    Merge one node that exists in neo4j and
    update the in-memory HeteroData accordingly.
    """
    # infra.ingest_node(req.node_type, req.node_id, req.features, req.edges)
    return {"status": "node ingested"}


@app.post("/gnn/graph/refresh", response_model=RefreshGraphResponse)
async def refresh_graph():
    """
    Diff Neo4j vs in-memory graph by ID and
    merge any new nodes/edges into HeteroData.
    """
    # diff = infra.fetch_diff()
    # stats = infra.apply_diff(diff)
    # return RefreshGraphResponse(**stats)
    return RefreshGraphResponse(
        status="graph refreshed", companies_added=0, profiles_added=0, edges_added=0
    )


# ─── VC FUNCTIONALITY ───────────────────────────────────────────────────────────
@app.post("/api/vc/companies/search")
async def search_companies(filters: VCFiltersRequest):
    """Search companies based on VC filters"""
    db = Neo4jDatabase()
    try:
        # Build dynamic query based on filters
        conditions = []
        params = {}
        
        if filters.industries:
            conditions.append("c.industry IN $industries")
            params["industries"] = filters.industries
        
        if filters.geo_regions:
            conditions.append("c.location IN $geo_regions")
            params["geo_regions"] = filters.geo_regions
        
        # Base query for companies
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        
        # Fixed query that avoids the aggregation in pattern comprehension issue
        query = f"""
        MATCH (c:Company)
        WHERE {where_clause}
        
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
        RETURN {
            urn: c.urn,
            name: c.name,
            industry: c.industry,
            employeeCount: employeeCount,
            recentTransitions: recentTransitions,
            growthRate: growthRate,
            churnRate: round(rand() * 15, 1)
        } as company
        ORDER BY employeeCount DESC
        LIMIT 50
        """
        
        results = db._run_query(query, params)
        companies = [r["company"] for r in results]
        
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
                companyUrn: c.urn,
                name: c.name,
                currentEmployees: currentEmployees,
                recentHires: recentHires,
                growthRate: round(100.0 * recentHires / (currentEmployees + 1), 2)
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
        # Modified query to handle null values correctly
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
        
        // Collect company data first
        WITH collect({
            urn: c.urn,
            name: c.name,
            employees: employees,
            departures: departures,
            arrivals: arrivals
        }) as companies
        
        // Calculate aggregated metrics after collecting companies
        WITH companies,
            reduce(total = 0, company in companies | total + company.employees) as totalEmployees,
            reduce(total = 0, company in companies | total + company.departures) as totalDepartures,
            reduce(total = 0, company in companies | total + company.arrivals) as totalArrivals
        
        RETURN {
            totalCompanies: size(companies),
            totalEmployees: totalEmployees,
            avgChurnRate: round(100.0 * totalDepartures / (CASE WHEN totalEmployees > 0 THEN totalEmployees ELSE 1 END), 2),
            netTalentFlow: totalArrivals - totalDepartures,
            companies: [company in companies | {
                urn: company.urn,
                name: company.name,
                employees: company.employees,
                churnRate: round(100.0 * company.departures / (CASE WHEN company.employees > 0 THEN company.employees ELSE 1 END), 2),
                netFlow: company.arrivals - company.departures
            }]
        } as overview
        """
        
        result = db._run_query(query, {"portfolio_ids": portfolio_ids})
        overview = result[0]["overview"] if result else {}
        
        # Identify at-risk companies
        at_risk = [comp for comp in overview.get("companies", []) 
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
        query = """
        MATCH (p:Profile)-[:HAS_SKILL]->(s:Skill)
        MATCH (p)-[:HAS_TRANSITION]->(t:Transition)
        WHERE t.date >= datetime() - duration('P6M')
        
        WITH s, count(p) as recentHires
        ORDER BY recentHires DESC
        LIMIT $limit
        
        MATCH (allProfiles:Profile)-[:HAS_SKILL]->(s)
        WITH s, recentHires, count(allProfiles) as totalProfiles
        
        RETURN {
            skill: s.name,
            recentHires: recentHires,
            totalProfiles: totalProfiles,
            trendScore: round(100.0 * recentHires / totalProfiles, 2)
        } as trendingSkill
        ORDER BY trendingSkill.trendScore DESC
        """
        
        results = db._run_query(query, {"limit": limit})
        trending_skills = [r["trendingSkill"] for r in results]
        
        return {
            "success": True,
            "skills": trending_skills
        }
    finally:
        db.close()
        
@app.post("/api/analytics/company-scores", response_model=List[CompanyScore])
async def calculate_company_scores(request: CompanyScoreRequest):
    """
    Calculate comprehensive company scores using PageRank, BiRank, and talent flow metrics.
    """
    try:
        db = Neo4jDatabase()
        
        # If no specific companies provided, get top companies
        if not request.company_urns:
            # Get all companies with minimum activity
            query = """
            MATCH (c:Company)
            WHERE exists((c)<-[:AT_COMPANY]-(:Experience)) 
            WITH c, count{(c)<-[:AT_COMPANY]-(:Experience)} as activity
            WHERE activity >= 5
            RETURN c.urn as urn, c.name as name
            ORDER BY activity DESC
            LIMIT 50
            """
            companies = db._run_query(query)
            company_urns = [c['urn'] for c in companies]
        else:
            company_urns = request.company_urns
        
        scores = []
        
        # 1. Calculate PageRank if requested
        pagerank_scores = {}
        if request.include_pagerank:
            # Create projection and run PageRank
            db.create_emp_company_projection(
                graph_name="scoring_graph",
                weight_scheme="count",
                delete_existing=True
            )
            
            # Run PageRank and get scores
            pagerank_df = db.pagerank_emp_company(
                graph_name="scoring_graph",
                damping=0.85,
                iterations=20
            )
            
            # Convert to dict for easy lookup
            for _, row in pagerank_df.iterrows():
                if row['name']:  # Filter out null names
                    # Find matching company URN
                    company_query = "MATCH (c:Company {name: $name}) RETURN c.urn as urn"
                    result = db._run_query(company_query, {"name": row['name']})
                    if result:
                        pagerank_scores[result[0]['urn']] = row['pagerank']
        
        # 2. Calculate BiRank if requested
        birank_scores = {}
        if request.include_birank:
            birank_df = db.birank_emp_company(
                graph_name="scoring_graph",
                alpha=0.85,
                beta=0.85,
                max_iter=20
            )
            
            # Process BiRank results
            for _, row in birank_df.iterrows():
                # Find matching company URN
                if row['label'] == 'Company':
                    company_query = "MATCH (c:Company) WHERE id(c) = $nodeId RETURN c.urn as urn, c.name as name"
                    result = db._run_query(company_query, {"nodeId": row['nodeId']})
                    if result:
                        urn = result[0]['urn']
                        if urn not in birank_scores:
                            birank_scores[urn] = {}
                        birank_scores[urn]['company_score'] = row['score']
                elif row['label'] == 'Profile':
                    # For employee scores, we need to aggregate by company
                    continue
        
        # 3. Calculate talent flow metrics if requested
        talent_flow_scores = {}
        if request.include_talent_flow:
            for company_urn in company_urns:
                talent_stats = db.get_company_transition_stats(company_urn)
                if talent_stats:
                    talent_flow_scores[company_urn] = {
                        'inflow': talent_stats.get('incomingTransitions', 0),
                        'outflow': talent_stats.get('outgoingTransitions', 0),
                        'net_flow': talent_stats.get('incomingTransitions', 0) - talent_stats.get('outgoingTransitions', 0)
                    }
        
        # 4. Combine all scores and calculate composite score
        for company_urn in company_urns:
            # Get company name
            company_query = "MATCH (c:Company {urn: $urn}) RETURN c.name as name"
            result = db._run_query(company_query, {"urn": company_urn})
            company_name = result[0]['name'] if result else "Unknown"
            
            # Get individual scores
            pagerank = pagerank_scores.get(company_urn, 0.0)
            birank_company = birank_scores.get(company_urn, {}).get('company_score', 0.0)
            birank_employee = birank_scores.get(company_urn, {}).get('employee_score', 0.0)
            
            talent_flow = talent_flow_scores.get(company_urn, {})
            inflow = talent_flow.get('inflow', 0)
            outflow = talent_flow.get('outflow', 0)
            net_flow = talent_flow.get('net_flow', 0)
            
            # Calculate composite score (weighted combination)
            composite_score = (
                pagerank * 0.3 +
                birank_company * 0.3 +
                min(net_flow / max(inflow + outflow, 1), 1.0) * 0.4
            )
            
            scores.append(CompanyScore(
                company_urn=company_urn,
                company_name=company_name,
                pagerank_score=pagerank,
                birank_company_score=birank_company,
                birank_employee_score=birank_employee,
                talent_inflow=inflow,
                talent_outflow=outflow,
                net_talent_flow=net_flow,
                composite_score=composite_score
            ))
        
        db.close()
        return sorted(scores, key=lambda x: x.composite_score, reverse=True)
        
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
async def company_deep_dive(request: CompanyDeepDiveRequest, current_user: User = Depends(get_current_user)):
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

@app.post("/api/analytics/talent-flow", response_model=TalentFlowResponse)
async def analyze_talent_flow(request: TalentFlowAnalysisRequest, current_user: User = Depends(get_current_user)):
    """
    Analyze talent flow patterns between companies and regions.
    
    This endpoint provides:
    - Network visualization data of talent movement
    - Aggregated talent flow metrics
    - Top source and destination companies
    - Historical talent flow trends
    """
    try:
        # Check cache if no specific filters
        cache_key = "talent_flow_network"
        if (not request.company_ids and not request.region_ids and 
            request.time_period == "all" and request.granularity == "month" and
            is_cache_valid(cache_key)):
            logger.info("Using cached talent flow network data")
            network_data = cache["talent_flow_network"]
        else:
            # Get start and end dates based on time period
            start_date, end_date = get_time_period_dates(request.time_period)
            
            # Build Neo4j query based on request parameters
            cypher_query = """
            MATCH (p:Profile)-[ht:HAS_TRANSITION]->(t:Transition)
            MATCH (t)-[:FROM_COMPANY]->(fc:Company)
            MATCH (t)-[:TO_COMPANY]->(tc:Company)
            WHERE t.transition_date >= $start_date
            AND t.transition_date <= $end_date
            """
            
            params = {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "min_transitions": request.min_transitions
            }
            
            # Add company filter if specified
            if request.company_ids:
                cypher_query += """
                AND (fc.company_urn IN $company_ids OR tc.company_urn IN $company_ids)
                """
                params["company_ids"] = request.company_ids
            
            # Add region filter if specified
            if request.region_ids:
                cypher_query += """
                AND (fc.region_id IN $region_ids OR tc.region_id IN $region_ids)
                """
                params["region_ids"] = request.region_ids
            
            # Aggregate transitions
            cypher_query += """
            WITH fc, tc, count(*) AS flow
            WHERE flow >= $min_transitions
            RETURN fc.company_urn AS source_id, 
                   fc.name AS source_name,
                   tc.company_urn AS target_id,
                   tc.name AS target_name,
                   flow
            ORDER BY flow DESC
            """
            
            # Execute query
            results = query_neo4j(cypher_query, params)
            
            # Process results into network format
            nodes = {}
            links = []
            
            # Process links and collect node IDs
            for result in results:
                source_id = result["source_id"]
                target_id = result["target_id"]
                
                # Skip self-links (promotions)
                if source_id == target_id:
                    continue
                
                # Add to nodes dictionary
                if source_id not in nodes:
                    nodes[source_id] = {
                        "id": source_id,
                        "name": result["source_name"],
                        "type": "company",
                        "outflow": 0,
                        "inflow": 0
                    }
                
                if target_id not in nodes:
                    nodes[target_id] = {
                        "id": target_id,
                        "name": result["target_name"],
                        "type": "company",
                        "outflow": 0,
                        "inflow": 0
                    }
                
                # Update node flow metrics
                nodes[source_id]["outflow"] += result["flow"]
                nodes[target_id]["inflow"] += result["flow"]
                
                # Add link
                links.append({
                    "source": source_id,
                    "target": target_id,
                    "value": result["flow"]
                })
            
            # Calculate net flow and convert nodes to list
            nodes_list = []
            for node_id, node_data in nodes.items():
                node_data["net_flow"] = node_data["inflow"] - node_data["outflow"]
                nodes_list.append(node_data)
            
            # Calculate summary metrics
            total_transitions = sum(link["value"] for link in links)
            avg_transitions = total_transitions / len(links) if links else 0
            
            # Identify companies with highest inflow and outflow
            sorted_inflow = sorted(nodes_list, key=lambda x: x["inflow"], reverse=True)
            sorted_outflow = sorted(nodes_list, key=lambda x: x["outflow"], reverse=True)
            
            top_sources = sorted_outflow[:5]
            top_destinations = sorted_inflow[:5]
            
            # Create summary
            summary = {
                "total_transitions": total_transitions,
                "total_companies": len(nodes),
                "avg_transitions_per_link": round(avg_transitions, 1),
                "time_period": request.time_period,
                "top_source": top_sources[0]["name"] if top_sources else None,
                "top_destination": top_destinations[0]["name"] if top_destinations else None
            }
            
            # Create network data object
            network_data = {
                "nodes": nodes_list,
                "links": links,
                "summary": summary,
                "top_sources": top_sources,
                "top_destinations": top_destinations
            }
            
            # Cache results if this is the default query
            if not request.company_ids and not request.region_ids and request.time_period == "all":
                cache["talent_flow_network"] = network_data
                cache["last_updated"][cache_key] = datetime.now()
        
        return TalentFlowResponse(**network_data)
        
    except Exception as e:
        logger.exception(f"Error in talent flow analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analytics/geographic", response_model=GeographicAnalysisResponse)
async def geographic_analysis(request: GeographicAnalysisRequest, current_user: User = Depends(get_current_user)):
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
