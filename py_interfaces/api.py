from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import os
import json
import uvicorn
from datetime import datetime

# Import your existing modules
from models import LinkedInProfile, LinkedInCompany
from neo4j_database import Neo4jDatabase, send_to_neo4j, send_transition_to_neo4j, query_neo4j
from druid_database import send_to_druid, send_transition_update
from main import LinkedInAPI
from mock_enhanced import LinkedInDataGenerator

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

# Define request models
class ProfileRequest(BaseModel):
    public_id: str

class SearchRequest(BaseModel):
    query: Dict[str, Any]
    description: Optional[str] = None

class TransitionEvent(BaseModel):
    profile_urn: str
    from_company_urn: str
    to_company_urn: str
    transition_date: str
    transition_type: str
    old_title: str
    new_title: str
    location_change: bool
    tenure_days: int

class MockGenerationConfig(BaseModel):
    num_profiles: int = 10
    store_in_db: bool = True
    career_distribution: Optional[Dict[str, float]] = None
    education_distribution: Optional[Dict[str, float]] = None

# Routes for health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "LinkedIn Data API is running"}

# # LinkedIn profile endpoints
# @app.post("/api/profile")
# async def get_profile(request: ProfileRequest):
#     """Get LinkedIn profile by public ID"""
#     profile_data = linkedin_api.get_profile_from_public_ID(request.public_id)
#     if not profile_data:
#         raise HTTPException(status_code=404, detail="Profile not found")
    
#     try:
#         profile = LinkedInProfile.parse_raw_profile(LinkedInProfile, profile_data)
#         return profile.model_dump()
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error parsing profile: {str(e)}")

# @app.post("/api/search")
# async def search_profiles(request: SearchRequest):
#     """Search LinkedIn profiles based on criteria"""
#     search_results = linkedin_api.search_profiles(**request.query)
    
#     if request.description:
#         # Filter profiles based on description if provided
#         filtered_results = linkedin_api.find(request.query, request.description)
#         return {"results": filtered_results}
    
#     return {"results": search_results}

# Database endpoints
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

# File upload endpoints
@app.post("/api/upload/resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and process a resume image"""
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads/resumes", exist_ok=True)
    
    # Save file
    file_path = f"uploads/resumes/{datetime.now().strftime('%Y%m%d%H%M%S')}-{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Here you would process the resume (OCR, data extraction, etc.)
    # This is a placeholder for your actual implementation
    
    return {
        "success": True,
        "filename": file.filename,
        "path": file_path,
        "message": "Resume uploaded successfully. Processing will occur asynchronously."
    }

@app.post("/api/upload/linkedin")
async def upload_linkedin(file: UploadFile = File(...)):
    """Upload and process a LinkedIn screenshot"""
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads/linkedin", exist_ok=True)
    
    # Save file
    file_path = f"uploads/linkedin/{datetime.now().strftime('%Y%m%d%H%M%S')}-{file.filename}"
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Here you would process the LinkedIn screenshot (OCR, data extraction, etc.)
    # This is a placeholder for your actual implementation
    
    return {
        "success": True,
        "filename": file.filename,
        "path": file_path,
        "message": "LinkedIn screenshot uploaded successfully. Processing will occur asynchronously."
    }

# Start the server if running as a script
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)