#!/usr/bin/env python3
"""
Spike Research - Main Entry Point
VC Research Platform for Talent Flow Analysis and Investment Intelligence

This application focuses on:
1. Aggregating employee transition data across companies
2. Building bipartite graphs (Employee ↔ Company) for analysis
3. Running graph algorithms (PageRank, BiRank) to identify influential companies
4. Providing infrastructure for Graph Neural Network research
5. Generating investment signals based on talent flow patterns

The core thesis: Individual employment decisions, when aggregated, can predict company success.
"""

import uvicorn
from spike_research.api.api import app

if __name__ == "__main__":
    print("🚀 Starting Spike Research API...")
    print("")
    
    uvicorn.run(
        "spike_research.api.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )