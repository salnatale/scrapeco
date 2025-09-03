# Spike Research Platform - Architecture & Decisions

*Last Updated: 2025-09-03*

## Platform Overview

**Spike Research** is a VC research platform that analyzes talent flow patterns between companies to generate investment intelligence. The core thesis: aggregating individual employment decisions through Graph Neural Networks (GNNs) can predict company success and identify investment opportunities.

## Key Architecture Decisions

### 1. Package Management: venv + pip-tools
**Current:** Standard venv with pip-tools for lock files  
**Why:** 
- Lightweight and universally supported
- Reproducible builds via `requirements.txt` lock file
- No overhead for small research project
- Easy CI/CD integration

**Files:**
- `.venv/` - Virtual environment
- `requirements.txt` - Auto-generated lock file
- `pyproject.toml` - Source dependencies

**Commands:**
```bash
# Update dependencies
pip-compile pyproject.toml --resolver=backtracking

# Install from lock file  
pip install -r requirements.txt
```

**When to switch:** Consider Poetry/pipenv if complex dependency conflicts arise or team grows significantly.

### 2. Database: Neo4j Graph Database
**Current:** Neo4j with Graph Data Science (GDS) library  
**Why:**
- Perfect for bipartite Employee↔Company graphs
- Built-in PageRank and advanced graph algorithms
- Mature ecosystem with Cypher query language
- GDS library essential for GNN feature engineering

**Alternative considered:** NetworkX + PostgreSQL (rejected - performance issues at scale)

**When to switch:** If moving to distributed graph processing (consider TigerGraph/Neptune)

### 3. Time-Series Analytics: Apache Druid
**Current:** Druid for transition event storage  
**Why:**
- Real-time ingestion of career transition events
- Fast aggregations for temporal analysis
- Complements Neo4j for time-based queries

**When to switch:** Consider ClickHouse if moving to pure SQL interface

### 4. API Framework: FastAPI
**Current:** FastAPI with Pydantic models  
**Why:**
- Automatic OpenAPI documentation
- Type safety with Pydantic
- High performance async support
- Perfect for research/prototype APIs

### 5. Code Quality: Ruff
**Current:** Ruff for linting and formatting  
**Why:**
- Extremely fast (10-100x faster than alternatives)
- Combines multiple tools (flake8, black, isort, etc.)
- Modern Python type hint support
- VS Code integration

**Commands:**
```bash
ruff check spike_research/          # Lint
ruff check spike_research/ --fix    # Auto-fix
ruff format spike_research/         # Format
```

## Core Data Models

### Employee (formerly LinkedInProfile)
Tracks professional profiles and career progression
```python
class Employee(BaseModel):
    profile_urn: str
    first_name: str
    last_name: str
    experience: list[Experience]
    education: list[Education]
```

### TransitionEvent
Core to investment thesis - tracks talent flow between companies
```python
class TransitionEvent(BaseModel):
    profile_urn: str
    from_company_urn: str
    to_company_urn: str
    transition_date: datetime
    seniority_change: int  # -1 (down), 0 (lateral), 1 (up)
```

### VC Models
```python
class Fund(BaseModel): ...
class Investment(BaseModel): ...
class Company(BaseModel): ...
```

## Backend Services

### Neo4j Graph Operations
- **Talent Flow Projections:** Create bipartite Employee↔Company graphs
- **PageRank Analysis:** Rank company influence by talent attraction
- **Custom Graph Algorithms:** Future GNN feature extraction

### Druid Time-Series
- **Transition Ingestion:** Real-time career change events
- **Temporal Analytics:** Time-based aggregations and trends

### FastAPI Endpoints
- `/api/company/{urn}/analysis` - Company talent metrics
- `/api/company/{urn}/signals` - Investment signals
- `/api/graph/pagerank` - Graph algorithm execution
- `/gnn/` - Future ML inference endpoints (stubs)

## System State

### ✅ Completed
- Core data models refactored for VC focus
- Neo4j graph operations (PageRank, talent flow)
- FastAPI API layer with comprehensive endpoints
- Ruff integration for code quality
- venv + pip-tools reproducible environment
- Shell auto-activation on directory change

### 🚧 In Progress
- None currently

### 📋 Planned
- GNN model implementation in `spike_research/gnn/`
- Production deployment configuration
- Comprehensive testing suite
- Data pipeline automation

## Development Environment

### Shell Setup
Auto-activates venv when entering project directory via `~/.zprofile`:
```bash
spike_venv() {
    if [[ "$PWD" == "$SPIKE_RESEARCH_PROJECT"* ]] && [[ "$VIRTUAL_ENV" != "$SPIKE_RESEARCH_PROJECT/.venv" ]]; then
        source "$SPIKE_RESEARCH_PROJECT/.venv/bin/activate"
        echo "🔬 Activated Spike Research environment"
    fi
}
```

### VS Code Integration
- Ruff extension for linting/formatting
- Python interpreter set to `.venv/bin/python`
- Format on save enabled
- Auto-organize imports

## Key Files Structure

```
spike_research/
├── core/
│   └── models.py          # Pydantic data models
├── database/
│   ├── neo4j_database.py  # Graph operations
│   └── druid_database.py  # Time-series operations
├── api/
│   └── api.py            # FastAPI endpoints
├── utils/
│   └── config.py         # Environment configuration
└── gnn/                  # Future ML models
```

## Codebase Transformation Summary

**From:** ScrapeEco (16,000+ lines) - Consumer LinkedIn scraping/resume parsing  
**To:** Spike Research (~2,000 lines) - VC research platform  

**Removed (~85%):**
- Frontend React/Express application
- PDF/PNG resume parsing (OCR)
- LinkedIn scraping infrastructure
- Mock data generation
- Security/authentication layers

**Retained/Refactored:**
- Core graph database infrastructure
- Employee transition tracking (fundamental to GNN thesis)
- Company and investment models
- API framework (simplified for research focus)

---

*This document is maintained by Claude and updated with each architectural change*