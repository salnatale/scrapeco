# ScrapeCo Data Analytics Platform

A comprehensive data analytics platform for company and talent analysis, focusing on VC portfolio management, talent flow visualization, and market intelligence.

## Features

- **Interactive Visualizations**: Geographic heatmaps, network graphs, and Sankey diagrams for talent and company data
- **Portfolio Analytics**: Track portfolio health scores, funding stages, and talent flows
- **Advanced Analytics**: Company deep-dives, talent flow analysis, and geographic trends 
- **AI-Powered Insights**: Get recommendations based on talent flow patterns and market trends

## System Architecture

The platform consists of:

1. **Frontend**: React-based components with D3.js visualizations
2. **Backend API**: FastAPI-based Python server with analytics endpoints
3. **Graph Database**: Neo4j for storing relationship data
4. **Time-Series Database**: Druid for storing time-series data (optional)

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 14+
- Neo4j Graph Database (4.4+)
- npm/yarn

### Backend Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/scrapeco.git
   cd scrapeco
   ```

2. **Set up the Python environment**:
   ```bash
   cd py_interfaces
   bash scripts/setup.sh
   ```

   To generate mock data during setup:
   ```bash
   bash scripts/setup.sh --generate-data
   ```

3. **Run the API server**:
   ```bash
   bash scripts/run_api.sh
   ```
   
   The API will be available at http://localhost:8000

4. **Test the API**:
   ```bash
   python scripts/test_api.py
   ```

### Frontend Setup

1. **Install frontend dependencies**:
   ```bash
   cd frontend/client
   npm install
   ```

2. **Start the frontend development server**:
   ```bash
   npm start
   ```
   
   The frontend will be available at http://localhost:3000

## API Documentation

You can access the FastAPI documentation at http://localhost:8000/docs.

Key API endpoints:

- `/api/analytics/company-deep-dive`: Comprehensive company analysis
- `/api/analytics/talent-flow`: Analyze talent flow patterns
- `/api/analytics/geographic`: Geographic distribution of talent
- `/api/vc/companies/search`: Search companies by criteria
- `/api/vc/portfolio/overview`: Portfolio company analysis

## Frontend Components

- **PortfolioMap**: Main visualization with geographic, network, and Sankey views
- **GeographicHeatmap**: Heatmap showing various metrics across regions
- **CompanyDeepDive**: Detailed company analysis dashboard
- **TalentFlowSankey**: Talent flow visualization between companies

## Data Model

The system uses the following key entities:

- **Companies**: Organization data including funding, size, industry
- **Profiles**: Professional profiles with skills, experiences, education
- **Transitions**: Career moves between companies
- **Skills**: Professional competencies and their trends

## Development

### Testing

Run backend tests with:
```bash
python scripts/test_api.py
```

### Customization

You can customize the visualization metrics and analysis parameters in:
- `frontend/client/src/components/PortfolioMap.js`
- `frontend/client/src/components/GeographicHeatmap.js`
- `py_interfaces/api.py`

### Production Deployment

For production deployment:

1. Build the frontend:
   ```bash
   cd frontend/client
   npm run build
   ```

2. Serve the static files with a web server like Nginx

3. Run the API with gunicorn:
   ```bash
   cd py_interfaces
   gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 api:app
   ```

## License

[MIT License](LICENSE)

## Contact

For questions and support, please contact [your-email@example.com].
