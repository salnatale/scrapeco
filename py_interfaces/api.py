from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
import os
import json
import uvicorn
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


#
# ─── Singletons ───────────────────────────────────────────────────────────────
#
gnn_trainer = None  # your training orchestrator
gnn_model = None  # loaded inference model
infra = None  # your GNN infrastructure instance


# Routes for health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "LinkedIn Data API is running"}


# ─── Ingest Dataset Endpoints ────────────────────────────────────────────────
#


@app.post("/api/process_corpus")
async def process_corpus(folder_path: str):
    """
    Process a local folder of .txt and image files and batch store parsed LinkedIn profiles and transitions.
    Each file is expected to be plain text or an image.
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
            status_code=404, detail="No .txt or image files found in the directory"
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
