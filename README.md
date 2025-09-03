# Spike Research - VC Research Platform

A venture capital research platform focused on analyzing talent flow patterns to predict company success through graph neural networks.

## Core Thesis

Individual employment decisions, when aggregated across thousands of professionals, reveal powerful signals about company health and future success. Our platform builds comprehensive bipartite graphs (Employee ↔ Company) and applies advanced graph algorithms to generate investment intelligence.

## Architecture

### Data Layer
- **Neo4j Graph Database**: Stores employee profiles, companies, and career transitions
- **Apache Druid**: Time-series analytics for transition events
- **Bipartite Graph Model**: Employee-Company relationships with weighted edges

### Analysis Layer  
- **PageRank Algorithm**: Identifies influential companies in talent networks
- **BiRank Algorithm**: Balanced ranking for bipartite graphs
- **Talent Flow Metrics**: Inflow/outflow ratios, net talent movement
- **Investment Signals**: Multi-factor scoring based on talent patterns

### Future: GNN Infrastructure
- **Graph Neural Networks**: Deep learning on talent flow graphs
- **Federated Learning**: Privacy-preserving partner data aggregation
- **Success Prediction**: ML models for investment outcomes

## Key Features

### 🔍 Talent Flow Analysis
- Track career transitions between companies
- Calculate talent inflow/outflow ratios
- Identify talent acquisition patterns
- Measure seniority progression trends

### 📊 Graph Analytics
- Build Employee-Company bipartite projections
- Run PageRank to find influential companies  
- Execute BiRank for balanced network analysis
- Generate company ranking dashboards

### 💼 Investment Intelligence
- Multi-factor investment signals
- Company analysis with talent metrics
- Integration with funding/exit data
- Predictive success indicators

### 🧠 Research Infrastructure
- Clean APIs for data ingestion
- Batch processing capabilities
- Custom Cypher query execution
- Extensible for GNN research

## Quick Start

1. **Setup Database**
```bash
# Start Neo4j and Druid instances
# Configure environment variables in .env

# Setup database schema
curl -X POST http://localhost:8000/api/db/setup
```

2. **Load Data** 
```bash
# Store employee profiles and transitions
curl -X POST http://localhost:8000/api/data/employees -d @employees.json
curl -X POST http://localhost:8000/api/data/transitions -d @transitions.json
```

3. **Run Analysis**
```bash  
# Create graph projection
curl -X POST http://localhost:8000/api/graph/projection

# Run PageRank analysis
curl -X POST http://localhost:8000/api/graph/pagerank

# Get company rankings
curl http://localhost:8000/api/graph/rankings
```

4. **Analyze Company**
```bash
# Get comprehensive company analysis
curl http://localhost:8000/api/company/{company_urn}/analysis

# Get investment signals
curl http://localhost:8000/api/company/{company_urn}/signals
```

## API Documentation

Start the server and visit: `http://localhost:8000/docs`

## Project Structure

```
spike_research/
├── core/           # Data models and business logic
├── database/       # Neo4j and Druid interfaces  
├── api/           # FastAPI application
├── gnn/           # Graph Neural Network infrastructure (future)
└── utils/         # Configuration and utilities
```

## Technology Stack

- **Backend**: Python, FastAPI, Pydantic
- **Graph Database**: Neo4j with GDS library
- **Time Series**: Apache Druid
- **ML Ready**: NetworkX, PyTorch Geometric (future)
- **Analytics**: pandas, numpy, scipy

## Development

```bash
# Install dependencies
pip install -r spike_research/requirements.txt

# Run development server
python main.py

# Run tests (when added)
pytest
```

## Vision

This platform provides the foundational infrastructure for sophisticated VC research, with the long-term goal of building Graph Neural Networks that can predict startup success by analyzing talent movement patterns across the entire technology ecosystem.

The core insight: where talented people choose to work reveals information about company prospects that traditional metrics cannot capture.