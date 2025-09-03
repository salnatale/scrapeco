from typing import Any, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import VC-focused modules
from ..core.models import (
    Company,
    Employee,
    Fund,
    Investment,
    TransitionEvent,
)
from ..database.druid_database import send_transition_update
from ..database.neo4j_database import create_database_connection


# Initialize FastAPI app
app = FastAPI(
    title="Spike Research API",
    description="VC Research Platform - Talent Flow Analysis and Investment Intelligence",
    version="2.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request/Response Models ──────────────────────────────────────────────


class TalentFlowRequest(BaseModel):
    company_urn: str


class GraphProjectionRequest(BaseModel):
    graph_name: str = "talent_flow"
    delete_existing: bool = False


class PageRankRequest(BaseModel):
    graph_name: str = "talent_flow"
    write_property: Optional[str] = None


class CompanyAnalysisResponse(BaseModel):
    company_name: str
    talent_inflow: int
    talent_outflow: int
    net_talent_flow: int
    talent_ratio: Optional[float]
    investment_profile: dict[str, Any]


class InvestmentSignalResponse(BaseModel):
    company_urn: str
    signal_strength: float
    factors: dict[str, Any]


# ─── Health Check ──────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Spike Research API is running",
        "version": "2.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db = create_database_connection()
        # Test database connection
        db.execute_query("MATCH (n) RETURN count(n) as total LIMIT 1")
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


# ─── Graph Operations ──────────────────────────────────────────────────


@app.post("/api/graph/projection")
async def create_graph_projection(request: GraphProjectionRequest):
    """Create talent flow graph projection for analysis"""
    try:
        db = create_database_connection()
        db.create_talent_flow_projection(
            graph_name=request.graph_name, delete_existing=request.delete_existing
        )
        db.close()
        return {"success": True, "graph_name": request.graph_name}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Graph projection failed: {str(e)}"
        )


@app.post("/api/graph/pagerank")
async def run_pagerank_analysis(request: PageRankRequest):
    """Run PageRank analysis on talent flow graph"""
    try:
        db = create_database_connection()
        results = db.run_pagerank(
            graph_name=request.graph_name, write_property=request.write_property
        )
        db.close()

        if request.write_property:
            return {"success": True, "message": "PageRank scores written to graph"}
        else:
            return {"success": True, "results": results.to_dict("records")}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"PageRank analysis failed: {str(e)}"
        )


@app.get("/api/graph/rankings")
async def get_company_rankings(metric: str = "pagerank_score", limit: int = 50):
    """Get top-ranked companies by specified metric"""
    try:
        db = create_database_connection()
        query = """
        MATCH (c:Company)
        WHERE c.`$metric` IS NOT NULL
        RETURN c.name as company_name,
               c.urn as company_urn,
               c.`$metric` as score,
               c.funding_stage as funding_stage,
               c.exit_status as exit_status
        ORDER BY score DESC
        LIMIT $limit
        """
        results = db.execute_query(query, {"metric": metric, "limit": limit})
        db.close()

        return {"metric": metric, "rankings": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rankings query failed: {str(e)}")


# ─── Company Analysis ──────────────────────────────────────────────────


@app.get("/api/company/{company_urn}/analysis", response_model=CompanyAnalysisResponse)
async def analyze_company(company_urn: str):
    """Comprehensive company analysis including talent flow and investment data"""
    try:
        db = create_database_connection()

        # Get talent flow metrics
        talent_metrics = db.get_talent_flow_metrics(company_urn)
        if not talent_metrics:
            raise HTTPException(status_code=404, detail="Company not found")

        # Get investment profile
        investment_profile = db.get_company_investment_profile(company_urn)

        db.close()

        return CompanyAnalysisResponse(
            company_name=talent_metrics.get("company_name", "Unknown"),
            talent_inflow=talent_metrics.get("talent_inflow", 0),
            talent_outflow=talent_metrics.get("talent_outflow", 0),
            net_talent_flow=talent_metrics.get("net_talent_flow", 0),
            talent_ratio=talent_metrics.get("talent_ratio"),
            investment_profile=investment_profile,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Company analysis failed: {str(e)}"
        )


@app.get("/api/company/{company_urn}/signals")
async def get_investment_signals(company_urn: str):
    """Generate investment signals based on talent flow and other factors"""
    try:
        db = create_database_connection()

        # Get basic metrics
        talent_metrics = db.get_talent_flow_metrics(company_urn)
        investment_profile = db.get_company_investment_profile(company_urn)

        if not talent_metrics:
            raise HTTPException(status_code=404, detail="Company not found")

        # Calculate signal strength (simplified algorithm)
        net_flow = talent_metrics.get("net_talent_flow", 0)
        talent_ratio = talent_metrics.get("talent_ratio", 0) or 0
        total_investments = investment_profile.get("total_investments", 0)

        # Simple scoring algorithm (to be enhanced with ML)
        signal_strength = min(
            100.0,
            max(0.0, (net_flow * 10) + (talent_ratio * 30) + (total_investments * 5)),
        )

        factors = {
            "net_talent_flow": net_flow,
            "talent_ratio": talent_ratio,
            "investment_activity": total_investments,
            "funding_stage": investment_profile.get("funding_stage"),
            "exit_status": investment_profile.get("exit_status"),
        }

        db.close()

        return InvestmentSignalResponse(
            company_urn=company_urn, signal_strength=signal_strength, factors=factors
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Signal generation failed: {str(e)}"
        )


# ─── Data Management ───────────────────────────────────────────────────


@app.post("/api/data/employees")
async def store_employees(employees: list[Employee]):
    """Store employee profiles"""
    try:
        db = create_database_connection()
        db.batch_store_employees(employees)
        db.close()
        return {"success": True, "stored": len(employees)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Employee storage failed: {str(e)}"
        )


@app.post("/api/data/transitions")
async def store_transitions(transitions: list[TransitionEvent]):
    """Store transition events"""
    try:
        db = create_database_connection()
        db.batch_store_transitions(transitions)
        db.close()

        # Also send to Druid for time-series analysis
        for transition in transitions:
            send_transition_update(transition.model_dump())

        return {"success": True, "stored": len(transitions)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Transition storage failed: {str(e)}"
        )


@app.post("/api/data/companies")
async def store_companies(companies: list[Company]):
    """Store company data"""
    try:
        db = create_database_connection()
        for company in companies:
            db.store_company(company)
        db.close()
        return {"success": True, "stored": len(companies)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Company storage failed: {str(e)}")


@app.post("/api/data/funds")
async def store_funds(funds: list[Fund]):
    """Store fund data"""
    try:
        db = create_database_connection()
        for fund in funds:
            db.store_fund(fund)
        db.close()
        return {"success": True, "stored": len(funds)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fund storage failed: {str(e)}")


@app.post("/api/data/investments")
async def store_investments(investments: list[Investment]):
    """Store investment relationships"""
    try:
        db = create_database_connection()
        for investment in investments:
            db.store_investment(investment)
        db.close()
        return {"success": True, "stored": len(investments)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Investment storage failed: {str(e)}"
        )


# ─── Custom Queries ────────────────────────────────────────────────────


@app.post("/api/query")
async def custom_query(query: dict[str, Any]):
    """Execute custom Cypher query"""
    if "cypher" not in query:
        raise HTTPException(status_code=400, detail="Query must include 'cypher' field")

    try:
        db = create_database_connection()
        results = db.execute_query(query["cypher"], query.get("params", {}))
        db.close()
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


# ─── GNN Endpoints (Stubs for Future ML Integration) ──────────────────


@app.post("/gnn/train")
async def train_gnn_model():
    """Train GNN model for investment prediction (stub)"""
    job_id = str(uuid4())
    return {
        "job_id": job_id,
        "status": "started",
        "message": "GNN training not implemented yet",
    }


@app.get("/gnn/predict/company/{company_urn}")
async def predict_company_success(company_urn: str):
    """Predict company success probability (stub)"""
    # Placeholder for GNN inference
    return {
        "company_urn": company_urn,
        "success_probability": 0.5,  # Placeholder
        "confidence": 0.0,
        "message": "GNN inference not implemented yet",
    }


@app.post("/gnn/predict/companies")
async def predict_companies_batch(company_urns: list[str]):
    """Batch prediction for multiple companies (stub)"""
    predictions = {
        urn: {"success_probability": 0.5, "confidence": 0.0} for urn in company_urns
    }
    return {
        "predictions": predictions,
        "message": "GNN batch inference not implemented yet",
    }


# ─── Database Management ───────────────────────────────────────────────


@app.post("/api/db/setup")
async def setup_database():
    """Setup database constraints and indexes"""
    try:
        db = create_database_connection()
        db.setup_constraints()
        db.close()
        return {"success": True, "message": "Database setup completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database setup failed: {str(e)}")


@app.post("/api/db/clear")
async def clear_database():
    """Clear all data from database (use with caution!)"""
    try:
        db = create_database_connection()
        db.clear_database()
        db.close()
        return {"success": True, "message": "Database cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database clear failed: {str(e)}")


# ─── Server Startup ────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
